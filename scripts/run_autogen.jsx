#target photoshop
var g_injected_images_dir = "D:/TAMDA/LetakMaster/workspaces/images";
var g_injected_json_dir = "D:/TAMDA/LetakMaster/workspaces/build_plans/260127_0133_Workspace_State_1.xlsx_State_1";
var g_injected_automation = true;

var scriptFolder = new File($.fileName).parent;
var projectRoot = scriptFolder.parent;
var LOG_FILE = new File(projectRoot.fsName + "/debug_manifest.txt");

function logToManifest(msg) {
    LOG_FILE.open('a'); // Append mode
    LOG_FILE.writeln(new Date().toTimeString() + ": " + msg);
    LOG_FILE.close();
}

// Utility: Read JSON
function readJSON(filePath) {
    logToManifest("Reading JSON: " + filePath);
    var file = new File(filePath);
    file.encoding = "UTF-8";
    file.open('r');
    var content = file.read();
    file.close();
    var obj = eval('(' + content + ')');
    logToManifest("JSON Parsed. Actions: " + (obj.actions ? obj.actions.length : "0"));
    return obj;
}

// Simple JSON Serializer for ExtendScript
function toJson(obj) {
    var t = typeof (obj);
    if (t != "object" || obj === null) {
        if (t == "string") obj = '"' + obj.replace(/"/g, '\\"') + '"';
        return String(obj);
    } else {
        var n, v, json = [], arr = (obj && obj.constructor == Array);
        for (n in obj) {
            v = obj[n];
            t = typeof (v);
            if (t == "string") v = '"' + v.replace(/"/g, '\\"') + '"';
            else if (t == "object" && v !== null) v = toJson(v);
            json.push((arr ? "" : '"' + n + '":') + String(v));
        }
        return (arr ? "[" : "{") + String(json) + (arr ? "]" : "}");
    }
}

function saveManifest(docPath, pageNum) {
    try {
        var scriptFolder = new File($.fileName).parent;
        var projectRoot = scriptFolder.parent;
        var f = new File(projectRoot.fsName + "/debug_manifest.json");
        f.open('w');
        f.write(toJson(g_manifest));
        f.close();
    } catch(e) { }
}

// --- Globals & Config ---
var g_injected_json_dir = typeof g_injected_json_dir !== 'undefined' ? g_injected_json_dir : null;
var g_injected_images_dir = typeof g_injected_images_dir !== 'undefined' ? g_injected_images_dir : null;
var g_injected_automation = typeof g_injected_automation !== 'undefined' ? g_injected_automation : false;

var g_imagesDir = null;
var g_config = {};
var g_manifest = [];

// Helper: Select Layer by ID
function selectLayerAM(id) {
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putIdentifier(charIDToTypeID("Lyr "), id);
    desc.putReference(charIDToTypeID("null"), ref);
    desc.putBoolean(charIDToTypeID("MkVs"), false);
    executeAction(charIDToTypeID("slct"), desc, DialogModes.NO);
}

// Helper: Safer Text Update (Selects + DOM)
function setTextAM(layerId, text) {
    try {
        selectLayerAM(layerId);
        var doc = app.activeDocument;
        if (doc.activeLayer.kind == LayerKind.TEXT) {
             doc.activeLayer.textItem.contents = text;
             logToManifest("setTextAM: Success " + layerId);
        } else {
             logToManifest("setTextAM: Active layer is not TEXT. ID: " + layerId + ", Kind: " + doc.activeLayer.kind);
        }
    } catch(e) {
        logToManifest("SetText Error (ID " + layerId + "): " + e);
    }
}

// Helper: Scan All Layers via ActionManager (The "Big Gun" optimization)
function scanLayersAM() {
    var map = {}; 
    
    try {
        var ref = new ActionReference();
        ref.putProperty(charIDToTypeID("Prpr"), charIDToTypeID("NmbL"));
        ref.putEnumerated(charIDToTypeID("Dcmn"), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        var desc = executeActionGet(ref);
        var count = desc.getInteger(charIDToTypeID("NmbL"));
        
        logToManifest("AM Scan: Found " + count + " layers.");
        
        var stack = [];
        
        // AM Indexes are 1-based, from Bottom to Top.
        // To build the hierarchy correctly (Start -> Content -> End), we must iterate Top to Bottom.
        // So we loop from count down to 1.
        for (var i = count; i >= 1; i--) {
            var layerRef = new ActionReference();
            layerRef.putIndex(charIDToTypeID("Lyr "), i);
            var layerDesc = executeActionGet(layerRef);
            
            var id = layerDesc.getInteger(charIDToTypeID("LyrI"));
            var name = layerDesc.getString(charIDToTypeID("Nm  "));
            
            var type = "content";
            if (layerDesc.hasKey(stringIDToTypeID("layerSection"))) {
                var ls = typeIDToStringID(layerDesc.getEnumerationValue(stringIDToTypeID("layerSection")));
                if (ls == "layerSectionStart") type = "groupStart";
                else if (ls == "layerSectionEnd") type = "groupEnd";
            }
            
            if (type == "groupStart") {
                var isProduct = (name.indexOf("Product_") === 0 || name.indexOf("A4_") === 0);
                
                var entry = { 
                    name: name,
                    isProduct: isProduct,
                    id: id,
                    flatChildren: {} 
                };
                
                if (isProduct) {
                    map[name] = entry.flatChildren;
                    map[name]["_self"] = id; 
                    logToManifest("AM Map: Found Group " + name + " (ID " + id + ")");
                }
                
                stack.push(entry);
                
            } else if (type == "groupEnd") {
                if (stack.length > 0) stack.pop();
                
            } else {
                for (var s = stack.length - 1; s >= 0; s--) {
                    if (stack[s].isProduct) {
                        var key = name.toLowerCase();
                        if (!stack[s].flatChildren[key]) {
                            stack[s].flatChildren[key] = id;
                        }
                        break; 
                    }
                }
            }
        }
    } catch(e) {
        logToManifest("AM Scan Error: " + e);
    }
    return map;
}

// Helper: Translate Layer by ID (Selects then translates)
function translateLayerAM(id, dx, dy) {
    selectLayerAM(id);
    var doc = app.activeDocument;
    var layer = doc.activeLayer;
    layer.translate(dx, dy);
}

// Helper: Set Visibility by ID
function setVisibleAM(id, visible) {
    var list = new ActionList();
    var ref = new ActionReference();
    ref.putIdentifier(charIDToTypeID("Lyr "), id);
    list.putReference(ref);
    var desc = new ActionDescriptor();
    desc.putList(charIDToTypeID("null"), list);
    executeAction(charIDToTypeID(visible ? "Shw " : "Hd  "), desc, DialogModes.NO);
}

// New Helper: Update Text using ID Map
function updateTextLayerAM(layerIdMap, layerName, text) {
    var layerId = null;
    var method = "Direct";

    layerId = layerIdMap[layerName.toLowerCase()];
    
    if (!layerId) {
        layerId = layerIdMap[layerName.toLowerCase() + "_k"];
        if (layerId) method = "Suffix_K";
    }
    if (!layerId) {
        layerId = layerIdMap[layerName.toLowerCase() + "k"];
        if (layerId) method = "Suffix_K_NoUnderscore";
    }
    if (!layerId) {
        layerId = layerIdMap[layerName.toLowerCase() + "_ex"];
        if (layerId) method = "Suffix_EX";
    }
    if (!layerId) {
        layerId = layerIdMap[layerName.toLowerCase() + "ex"];
        if (layerId) method = "Suffix_EX_NoUnderscore";
    }
    
    if (!layerId && layerName.indexOf("EAN") >= 0) {
        var vars = ["ean", "ean:", "ean_label"];
        for (var i=0; i<vars.length; i++) {
             if (layerIdMap[vars[i]]) {
                 layerId = layerIdMap[vars[i]];
                 method = "Fallback_Var_" + vars[i];
                 break;
             }
        }
    }

    if (layerId) {
        // Sanitize Text
        var safeText = text.toString();
        safeText = safeText.replace(/\\n/g, "\r");
        safeText = safeText.replace(/\r\n/g, "\r").replace(/\n/g, "\r");
        
        logToManifest("Updating " + layerName + " (ID: " + layerId + ") with: " + safeText);
        
        // Use Safer Setter
        setTextAM(layerId, safeText);
        
        return { id: layerId, text: safeText };
    } else {
        logToManifest("Failed to find layer ID for: " + layerName + " (Method: " + method + ")");
    }
    
    return null;
}

function findImageFile(dir, basename) {
    var extensions = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".psd", ".webp"];
    var f = new File(dir.fsName + "/" + basename);
    if (f.exists) return f;
    
    for (var i = 0; i < extensions.length; i++) {
        f = new File(dir.fsName + "/" + basename + extensions[i]);
        if (f.exists) return f;
        f = new File(dir.fsName + "/" + basename + extensions[i].toUpperCase());
        if (f.exists) return f;
    }
    return null;
}

function placeAndAlign(doc, group, placeholder, file) {
    try {
        var bounds = placeholder.bounds; 
        var pLeft = bounds[0].value;
        var pTop = bounds[1].value;
        var pRight = bounds[2].value;
        var pBottom = bounds[3].value;
        
        var pWidth = pRight - pLeft;
        var pHeight = pBottom - pTop;
        var pCenterX = pLeft + (pWidth / 2);
        var pCenterY = pTop + (pHeight / 2);

        doc.activeLayer = placeholder;
        
        var idPlc = charIDToTypeID("Plc ");
        var desc = new ActionDescriptor();
        var idnull = charIDToTypeID("null");
        desc.putPath(idnull, file);
        var idFTcs = charIDToTypeID("FTcs");
        var idQCSt = charIDToTypeID("QCSt");
        var idQcsa = charIDToTypeID("Qcsa");
        desc.putEnumerated(idFTcs, idQCSt, idQcsa); 
        executeAction(idPlc, desc, DialogModes.NO);
        
        var newLayer = doc.activeLayer;
        
        var nBounds = newLayer.bounds;
        var nWidth = nBounds[2].value - nBounds[0].value;
        var nHeight = nBounds[3].value - nBounds[1].value;
        
        if (nWidth > 0 && nHeight > 0) {
            var wRatio = pWidth / nWidth;
            var hRatio = pHeight / nHeight;
            var scale = Math.min(wRatio, hRatio) * 100;
            newLayer.resize(scale, scale, AnchorPosition.MIDDLECENTER);
        }
        
        nBounds = newLayer.bounds;
        var nLeft = nBounds[0].value;
        var nTop = nBounds[1].value;
        var nRight = nBounds[2].value;
        var nBottom = nBounds[3].value;
        
        var nCenterX = nLeft + ((nRight - nLeft) / 2);
        var nCenterY = nTop + ((nBottom - nTop) / 2);
        
        var dx = pCenterX - nCenterX;
        var dy = pCenterY - nCenterY;
        
        newLayer.translate(dx, dy);
        
        placeholder.visible = false;
        
    } catch(e) { }
}

function replaceProductImageAM(layerMap, imageName, imageDir) {
    var file = findImageFile(imageDir, imageName);
    if (!file) return;
    
    var baseNames = ["image", "obraz", "photo", "packshot"];
    var targetId = null;
    
    for (var key in layerMap) {
        if (key == "_self") continue;
        for (var b=0; b<baseNames.length; b++) {
            if (key.indexOf(baseNames[b]) >= 0) {
                targetId = layerMap[key];
                break;
            }
        }
        if (targetId) break;
    }
    
    if (targetId) {
        selectLayerAM(targetId);
        var doc = app.activeDocument;
        var placeholder = doc.activeLayer; 
        placeAndAlign(doc, null, placeholder, file);
    }
}

// ... (Existing Imports and Helpers) ...

// Helper: Duplicate Layer/Group by ID
function duplicateLayerAM(id) {
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putIdentifier(charIDToTypeID("Lyr "), id);
    desc.putReference(charIDToTypeID("null"), ref);
    executeAction(charIDToTypeID("Dplc"), desc, DialogModes.NO);
    return app.activeDocument.activeLayer.id; // Return ID of new copy (usually active)
}

// Helper: Rename Layer by ID
function renameLayerAM(id, newName) {
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putIdentifier(charIDToTypeID("Lyr "), id);
    desc.putReference(charIDToTypeID("null"), ref);
    var desc2 = new ActionDescriptor();
    desc2.putString(charIDToTypeID("Nm  "), newName);
    desc.putObject(charIDToTypeID("T   "), charIDToTypeID("Lyr "), desc2);
    executeAction(charIDToTypeID("setd"), desc, DialogModes.NO);
}

// Helper: Get Layer Name by ID
function getLayerNameAM(id) {
    var ref = new ActionReference();
    ref.putIdentifier(charIDToTypeID("Lyr "), id);
    return executeActionGet(ref).getString(charIDToTypeID("Nm  "));
}

// Helper: Process A4 Groups (Duplication & Renaming)
function processA4Groups(doc, plan) {
    // 1. Check if we need A4 logic
    var hasA4 = false;
    var maxGrp = 0;
    
    for (var i=0; i<plan.actions.length; i++) {
        var grp = plan.actions[i].group;
        if (grp.indexOf("A4_Grp_") === 0) {
            hasA4 = true;
            var num = parseInt(grp.split("_")[2], 10);
            if (num > maxGrp) maxGrp = num;
        }
    }
    
    if (!hasA4) return false; // No change needed
    
    logToManifest("A4 Groups Detected. Max Index: " + maxGrp);
    
    // 2. Find Template "A4_01"
    var map = scanLayersAM();
    var templateId = null;
    
    // Use "A4_01" as the primary template name
    if (map["A4_01"]) templateId = map["A4_01"]["_self"];
    if (!templateId && map["A4"]) templateId = map["A4"]["_self"]; // Fallback
    
    if (!templateId) {
        logToManifest("CRITICAL: 'A4_01' Template Group not found. Skipping A4 generation.");
        return false;
    }
    
    // 3. Generate Groups
    // We assume Template corresponds to Index 01.
    // We need to generate 02, 03... maxGrp.
    
    var didChange = false;
    
    for (var i=2; i<=maxGrp; i++) {
        var suffix = (i < 10) ? "0" + i : "" + i;
        var targetName = "A4_Grp_" + suffix;
        
        if (map[targetName]) {
            logToManifest("Group " + targetName + " already exists. Skipping.");
            continue;
        }
        
        logToManifest("Generating " + targetName + "...");
        
        // Select Template
        selectLayerAM(templateId);
        
        // Duplicate
        duplicateLayerAM(templateId);
        var newGroupId = app.activeDocument.activeLayer.id; // The duplicate is active
        
        // Rename Group
        renameLayerAM(newGroupId, targetName);
        
        // Rename Children
        // We need to scan again or just traverse children of the active group?
        // Using scanLayersAM is safer but slow inside a loop.
        // Let's use DOM for children renaming since we have the group active
        var activeGroup = app.activeDocument.activeLayer;
        
        // Helper to recurse and rename
        function renameChildren(layerObj, oldIdx, newIdx) {
             for (var k=0; k<layerObj.layers.length; k++) {
                 var child = layerObj.layers[k];
                 var oldName = child.name;
                 // Replace "_01" with "_XX" (e.g. nazev_01A_A -> nazev_02A_A)
                 // Be careful not to replace wrong parts. 
                 // Expectation: layer names contain "_01".
                 if (oldName.indexOf("_" + oldIdx) >= 0) {
                     var newLName = oldName.replace("_" + oldIdx, "_" + newIdx);
                     child.name = newLName;
                 }
                 
                 if (child.typename == "LayerSet") {
                     renameChildren(child, oldIdx, newIdx);
                 }
             }
        }
        
        renameChildren(activeGroup, "01", suffix);
        
        didChange = true;
    }
    
    return didChange; // Return true to trigger re-scan
}

function runBuild(doc, plan) {
    logToManifest("runBuild Started for Page " + plan.page);
    var total = plan.actions.length;
    
    var win = new Window("palette", "LetakMaster Builder");
    win.pnl = win.add("panel", [10, 10, 440, 100], "Building Page " + plan.page);
    win.pnl.progBar = win.pnl.add("progressbar", [20, 35, 410, 60], 0, total);
    win.pnl.lblStatus = win.pnl.add("statictext", [20, 20, 410, 35], "Scanning Document...");
    
    win.show();
    
    // --- Pre-Process A4 Groups ---
    var isA4Mode = false;
    try {
        if (processA4Groups(doc, plan)) {
            logToManifest("A4 Structure Generated. Re-scanning...");
            isA4Mode = true;
        } else {
            // Check if A4 groups exist in plan even if no generation happened (e.g. only 01 used)
            for (var i=0; i<plan.actions.length; i++) {
                if (plan.actions[i].group.indexOf("A4_Grp_") === 0) {
                    isA4Mode = true;
                    break;
                }
            }
        }
    } catch(e) {
        logToManifest("A4 Generation Error: " + e);
    }
    
    logToManifest("Scanning Layers AM...");
    var docMap = scanLayersAM();
    logToManifest("Scan Complete.");

    // If A4 Mode, Hide Standard Products
    if (isA4Mode) {
        logToManifest("A4 Mode Active: Hiding Standard Product Groups...");
        for (var i=1; i<=16; i++) {
            var suffix = (i < 10) ? "0" + i : "" + i;
            // Only hide the main parent group. If variants are nested, this hides them too.
            // If they are siblings, they might remain visible, but usually they are nested or strictly managed.
            // User requested to preserve inner visibility state.
            var baseName = "Product_" + suffix;
            if (docMap[baseName]) {
                setVisibleAM(docMap[baseName]["_self"], false);
            }
        }
    }

    // ... (rest of hideVariantsAM) ...

    function hideVariantsAM(currentGroupName, hero) {
        var id = parseInt(currentGroupName.replace("Product_", "").replace("A4_Grp_", ""), 10);
        // ... (rest of function logic needs adjustment for A4?) ...
        // Actually A4 groups don't have variants (K/EX) mentioned in the prompt, 
        // they are single "price tag groups". 
        // So we can leave this logic mostly for Standard Products.
        // But we should ensure it doesn't crash if it parses "A4_Grp_01" -> id=1.
        
        // Standard logic assumes Product_XX. 
        if (currentGroupName.indexOf("Product_") === -1) return; // Skip hiding for non-Standard groups
        
        var suffixId = (id < 10) ? "0" + id : "" + id;
        // ... (rest of standard logic) ...
        
        var variants = [
            "Product_" + suffixId, 
            "Product_" + suffixId + "_K", 
            "Product_" + suffixId + "_EX"
        ];
        
        for (var v=0; v<variants.length; v++) {
            if (variants[v] != currentGroupName) {
                if (docMap[variants[v]]) setVisibleAM(docMap[variants[v]]["_self"], false);
            }
        }
        
        var toHide = [];
        if (hero == 2) toHide.push(id + 4);
        else if (hero == 4) { toHide.push(id + 1); toHide.push(id + 4); toHide.push(id + 5); }
        
        for (var i=0; i<toHide.length; i++) {
            var hId = toHide[i];
            if (hId <= 16) {
                var s = (hId < 10) ? "0" + hId : "" + hId;
                var base = "Product_" + s;
                if (docMap[base]) setVisibleAM(docMap[base]["_self"], false);
                if (docMap[base+"_K"]) setVisibleAM(docMap[base+"_K"]["_self"], false);
                if (docMap[base+"_EX"]) setVisibleAM(docMap[base+"_EX"]["_self"], false);
            }
        }
    }

    logToManifest("Starting Action Processing (Total: " + total + ")");

    for (var i = 0; i < total; i++) {
        var action = plan.actions[i];
        var groupName = action.group;
        
        // Map "A4_Grp_01" to "A4" if needed?
        // Actually our processA4Groups ensures "A4_Grp_01" exists (via rename or alias?)
        // Wait, processA4Groups duplicates 02...MAX. 
        // What about 01?
        // If "A4" is the template, we should probably treat "A4" AS "A4_Grp_01".
        // SO if action asks for "A4_Grp_01" but map only has "A4", we map it.
        
        var targetGroup = groupName;
        if (groupName === "A4_Grp_01" && !docMap[groupName] && docMap["A4_01"]) {
            targetGroup = "A4_01";
        } else if (groupName === "A4_Grp_01" && !docMap[groupName] && docMap["A4"]) {
            targetGroup = "A4";
        }
        
        logToManifest("Processing Action: " + groupName + " (Target: " + targetGroup + ")");
        
        if (i % 3 === 0 || i === total - 1) {
            win.pnl.progBar.value = i + 1;
            win.pnl.lblStatus.text = "Processing " + groupName + " (" + (i + 1) + "/" + total + ")...";
            win.update(); 
        }
        
        var groupLayers = docMap[targetGroup];
        if (!groupLayers) {
            logToManifest("WARNING: Group " + targetGroup + " not found in DocMap.");
            continue;
        }
        
        try {
            if (groupLayers["_self"]) {
                setVisibleAM(groupLayers["_self"], true);
            }
            
            // Only run hideVariants for Products
            if (targetGroup.indexOf("Product_") === 0) {
                 hideVariantsAM(targetGroup, action.hero);
            }
            
            var shiftCandidates = {}; 

            for (var key in action.data) {
                // logToManifest("Processing Key: " + key); 
                if (key.indexOf("image_") === 0) {
                    if (g_imagesDir) {
                        replaceProductImageAM(groupLayers, action.data[key], g_imagesDir);
                    }
                } else {
                    var result = updateTextLayerAM(groupLayers, key, action.data[key]);
                    
                    if (result && key.toLowerCase().indexOf("nazev_") >= 0) {
                        var parts = key.split("_");
                        if (parts.length >= 2) {
                            var idPart = parts[1]; 
                            var lastChar = idPart.charAt(idPart.length - 1).toUpperCase();
                            var baseId = idPart.substring(0, idPart.length - 1);
                            
                            if (!shiftCandidates[baseId]) {
                                shiftCandidates[baseId] = { idA: null, textA: "", idB: null, textB: "" };
                            }
                            
                            if (lastChar === "A") {
                                shiftCandidates[baseId].idA = result.id;
                                shiftCandidates[baseId].textA = result.text;
                            } else if (lastChar === "B") {
                                shiftCandidates[baseId].idB = result.id;
                                shiftCandidates[baseId].textB = result.text;
                            }
                        }
                    }
                }
            }
            
            // ... (Rest of loop) ...
            
            for (var baseId in shiftCandidates) {
                var cand = shiftCandidates[baseId];
                if (cand.idA && cand.idB) {
                    var lenA = cand.textA.length;
                    var firstLineB = cand.textB.split('\r')[0];
                    var lenB = firstLineB.length;
                    
                    if (lenA < 13 && lenB < 18) {
                        translateLayerAM(cand.idA, 0, 30);
                        translateLayerAM(cand.idB, 0, 30);
                    }
                }
            }
            
            if (action.visibility) {
                for (var key in action.visibility) {
                    var lowerKey = key.toLowerCase();
                    var layerId = groupLayers[lowerKey];
                    
                    if (!layerId) layerId = groupLayers[lowerKey + "_k"];
                    if (!layerId) layerId = groupLayers[lowerKey + "k"];
                    if (!layerId) layerId = groupLayers[lowerKey + "_ex"];
                    if (!layerId) layerId = groupLayers[lowerKey + "ex"];

                    if (layerId) {
                        setVisibleAM(layerId, action.visibility[key]);
                    }
                }
            }
            
        } catch(e) {
            logToManifest("Error processing group " + groupName + ": " + e);
        }
    }
    
    win.close();
}

function main() {
    logToManifest("Script Started");
    var originalDisplayDialogs = app.displayDialogs;
    app.displayDialogs = DialogModes.NO;
    var originalRulerUnits = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;
    
    try {
        if (g_injected_images_dir) {
            var d = new Folder(g_injected_images_dir);
            if (d.exists) g_imagesDir = d;
        }

        if (!g_imagesDir) {
            var scriptPath = File($.fileName).parent.fsName;
            var configFile = new File(scriptPath + "/config.json");
            if (configFile.exists) {
                try {
                    g_config = readJSON(configFile.fsName);
                    if (g_config.images_dir) {
                        var d = new Folder(g_config.images_dir);
                        if (d.exists) g_imagesDir = d;
                    }
                } catch(e) { }
            }
        }

        var mode = "select";
        if (app.documents.length > 0) {
            if (g_injected_automation) {
                mode = "active";
            } else {
                var result = confirm("Process ACTIVE document '" + app.activeDocument.name + "'?\n\nClick YES to process Active Document.\nClick NO to Select Files from disk.");
                if (result) mode = "active";
            }
        }
        
        logToManifest("Mode: " + mode);
        if (mode == "active") {
            processDocument(app.activeDocument);
        } else {
            var files = File.openDialog("Select PSD Files to Automate", "*.psd", true);
            if (files && files.length > 0) {
                for (var i = 0; i < files.length; i++) {
                    var doc = open(files[i]);
                    processDocument(doc);
                }
            }
        }
    } finally {
        app.displayDialogs = originalDisplayDialogs;
        app.preferences.rulerUnits = originalRulerUnits;
    }
}

function updateAllTextLayers() {
    try {
        var idupdateAllTextLayers = stringIDToTypeID( "updateAllTextLayers" );
        var desc = new ActionDescriptor();
        executeAction( idupdateAllTextLayers, desc, DialogModes.NO );
    } catch(e) { }
}

function processDocument(doc) {
    app.activeDocument = doc;
    updateAllTextLayers();
    
    var docName = doc.name;
    var pageNum = null;
    var match = docName.match(/Page\s*(\d+)/i);
    
    if (match && match[1]) {
        pageNum = parseInt(match[1], 10);
    }
    
    if (!pageNum || isNaN(pageNum)) {
        alert("Skipping '" + docName + "': Could not detect 'Page XX' in filename.");
        return;
    }
    
    var jsonName = "build_page_" + pageNum + ".json";
    var scriptPath = File($.fileName).parent.fsName;
    var projectRoot = new Folder(scriptPath + "/.."); 
    var jsonFile = null;
    
    if (g_injected_json_dir) {
        var d = new Folder(g_injected_json_dir);
        if (d.exists) {
             var f = new File(d.fsName + "/" + jsonName);
             if (f.exists) jsonFile = f;
        }
    }
    
    if (!jsonFile && g_config.json_dir) {
        var d = new Folder(g_config.json_dir);
        if (d.exists) {
             var f = new File(d.fsName + "/" + jsonName);
             if (f.exists) jsonFile = f;
        }
    }
    
    if (!jsonFile) {
        var plansRoot = new Folder(projectRoot.fsName + "/workspaces/build_plans");
        if (plansRoot.exists) {
            // New Scheme: YYMMDD_HHMM_...
            var allFolders = plansRoot.getFiles(function(f) { return f instanceof Folder; });
            var candidateFolders = [];
            
            for (var k = 0; k < allFolders.length; k++) {
                // Filter for folders starting with digits (timestamp)
                if (allFolders[k].name.match(/^\d{6}_\d{4}_/)) {
                    candidateFolders.push(allFolders[k]);
                }
            }
            
            if (candidateFolders.length > 0) {
                candidateFolders.sort(); // Lexicographical sort works for YYMMDD
                var selectedFolder = candidateFolders[candidateFolders.length - 1];
                if (selectedFolder) {
                    var potentialFile = new File(selectedFolder.fsName + "/" + jsonName);
                    if (potentialFile.exists) jsonFile = potentialFile;
                }
            }

            // Fallback: Legacy "state_X" folders
            if (!jsonFile) {
                var stateFolders = plansRoot.getFiles("state_*");
                if (stateFolders.length > 0) {
                    stateFolders.sort();
                    var selectedFolder = stateFolders[stateFolders.length - 1]; 
                    if (selectedFolder) {
                        var potentialFile = new File(selectedFolder.fsName + "/" + jsonName);
                        if (potentialFile.exists) jsonFile = potentialFile;
                    }
                }
            }
        }
    }
    
    if (!jsonFile) {
        var directPaths = [
            doc.path + "/" + jsonName,
            scriptPath + "/" + jsonName,
            projectRoot.fsName + "/" + jsonName
        ];
        for (var i = 0; i < directPaths.length; i++) {
            var f = new File(directPaths[i]);
            if (f.exists) { jsonFile = f; break; }
        }
    }
    
    if (!jsonFile) {
        alert("Could not auto-locate " + jsonName + ".\nPlease select the Build Plan JSON file manually.");
        jsonFile = File.openDialog("Select " + jsonName, "*.json");
    }
    
    if (!jsonFile) return;

    var plan = readJSON(jsonFile.fsName);

    if (!g_imagesDir) {
        g_imagesDir = Folder.selectDialog("Select the directory containing Product Images");
    }
    
    g_manifest = [];
    doc.suspendHistory("Build Page " + pageNum, "runBuild(doc, plan)");
    saveManifest(jsonFile.fsName, pageNum);
}

main();
