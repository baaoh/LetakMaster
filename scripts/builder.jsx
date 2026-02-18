#target photoshop

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

// Helper: Title Case Converter (Removes ALL CAPS)
function formatTitleCase(str) {
    if (!str) return "";
    var words = str.toLowerCase().split(' ');
    for (var i = 0; i < words.length; i++) {
        if (words[i].length > 0) {
            words[i] = words[i].charAt(0).toUpperCase() + words[i].slice(1);
        }
    }
    return words.join(' ');
}

// Helper: Robust Layer ID Lookup
function findLayerId(layerIdMap, layerName) {
    var lowerName = layerName.toLowerCase();
    
    // Helper to check map with variants (space/underscore/colon)
    function checkVariants(name) {
        if (layerIdMap[name]) return layerIdMap[name];
        
        var variants = [
            name.replace(/_/g, " "),
            name.replace(/ /g, "_"),
            name.replace(/:/g, ""),
            name.replace(/ /g, ": "),
            name.replace(/_/g, ": ")
        ];
        
        for (var i = 0; i < variants.length; i++) {
            if (layerIdMap[variants[i]]) return layerIdMap[variants[i]];
        }
        return null;
    }

    var layerId = checkVariants(lowerName);
    
    // Suffixes to try (for Grid K/EX and A4 A/B)
    var suffixes = ["_k", " k", "k", "_ex", " ex", "ex", "_a", " a", "a", "_b", " b", "b"];

    // 1. Try common suffixes if not found directly
    if (!layerId) {
        for (var i = 0; i < suffixes.length; i++) {
            layerId = checkVariants(lowerName + suffixes[i]);
            if (layerId) break;
        }
    }
    
    // 2. Specialized Fallbacks for EAN
    if (!layerId && lowerName.indexOf("ean") >= 0) {
        var baseSuffix = "";
        var match = lowerName.match(/[_ ](\w+)$/);
        if (match) baseSuffix = match[1];

        var eanVars = ["ean", "ean:", "ean_label", "ean-number", "ean number"];
        for (var i = 0; i < eanVars.length; i++) {
            var v = eanVars[i];
            
            // Try with suffix variations (e.g., EAN_01)
            var baseCandidates = [v + "_" + baseSuffix, v + " " + baseSuffix, v + baseSuffix, v];
            for (var c = 0; c < baseCandidates.length; c++) {
                layerId = checkVariants(baseCandidates[c]);
                if (layerId) break;
                
                // Try with grid suffixes (e.g., EAN_01_K)
                for (var s = 0; s < suffixes.length; s++) {
                    layerId = checkVariants(baseCandidates[c] + suffixes[s]);
                    if (layerId) break;
                }
                if (layerId) break;
            }
            if (layerId) break;
        }
    }

    // 3. Specialized Fallbacks for Dostupnost
    if (!layerId && lowerName.indexOf("dostupnost") >= 0) {
        var baseSuffix = "";
        var match = lowerName.match(/[_ ](\w+)$/);
        if (match) baseSuffix = match[1];
        
        var v = "dostupnost";
        var baseCandidates = [v + "_" + baseSuffix, v + " " + baseSuffix, v + baseSuffix, v];
        for (var c = 0; c < baseCandidates.length; c++) {
            layerId = checkVariants(baseCandidates[c]);
            if (layerId) break;
            
            for (var s = 0; s < suffixes.length; s++) {
                layerId = checkVariants(baseCandidates[c] + suffixes[s]);
                if (layerId) break;
            }
            if (layerId) break;
        }
    }
    
    return layerId;
}

// New Helper: Update Text using ID Map
function updateTextLayerAM(layerIdMap, layerName, text) {
    var layerId = findLayerId(layerIdMap, layerName);
    
    // Fallback: If not found and name contains an underscore variant (e.g., nazev_01A_K),
    // try removing the last part to see if findLayerId can find it via its own heuristics.
    if (!layerId && layerName.indexOf("_") >= 0) {
        var parts = layerName.split("_");
        if (parts.length > 2) {
            var baseName = parts.slice(0, -1).join("_");
            layerId = findLayerId(layerIdMap, baseName);
        }
    }

    if (layerId) {
        // Sanitize Text
        var safeText = text.toString();
        
        // Remove ALL CAPS for Main Title Layers (containing "nazev" and "A")
        if (layerName.toLowerCase().indexOf("nazev") >= 0 && layerName.toUpperCase().indexOf("A") >= 0) {
            // Check if string is largely ALL CAPS
            if (safeText === safeText.toUpperCase() && safeText.length > 2) {
                safeText = formatTitleCase(safeText);
            }
        }

        safeText = safeText.replace(/\\n/g, "\r");
        safeText = safeText.replace(/\r\n/g, "\r").replace(/\n/g, "\r");
        
        logToManifest("Updating " + layerName + " (ID: " + layerId + ") with: " + safeText);
        
        // Use Safer Setter
        setTextAM(layerId, safeText);
        
        return { id: layerId, text: safeText };
    } else {
        logToManifest("Failed to find layer ID for: " + layerName);
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

// Helper: Set Layer Label Color
function setLayerLabelColorAM(id, colorStr) {
    try {
        var desc = new ActionDescriptor();
        var ref = new ActionReference();
        ref.putIdentifier(charIDToTypeID("Lyr "), id);
        desc.putReference(charIDToTypeID("null"), ref);
        var desc2 = new ActionDescriptor();
        desc2.putEnumerated(charIDToTypeID("Clr "), charIDToTypeID("Clr "), stringIDToTypeID(colorStr.toLowerCase()));
        desc.putObject(charIDToTypeID("T   "), charIDToTypeID("Lyr "), desc2);
        executeAction(charIDToTypeID("setd"), desc, DialogModes.NO);
    } catch(e) {
        logToManifest("Color Error: " + e);
    }
}

function replaceProductImageAM(layerMap, imageNamesStr, imageDir, colorLabel) {
    if (!imageNamesStr) return;
    
    var imageNames = imageNamesStr.toString().split('\n');
    var baseNames = ["image", "obraz", "photo", "packshot"];
    var exPlaceholderBase = "exsmartobject";
    
    for (var i = 0; i < imageNames.length; i++) {
        var imageName = imageNames[i];
        if (!imageName || imageName.length === 0) continue;
        
        var file = findImageFile(imageDir, imageName);
        if (!file) {
            logToManifest("Image not found: " + imageName);
            continue;
        }
        
        var targetId = null;
        
        // 1. Try to find EX-specific placeholder first (highest priority)
        for (var key in layerMap) {
            if (key == "_self") continue;
            if (key.indexOf(exPlaceholderBase) >= 0) {
                targetId = layerMap[key];
                logToManifest("Found EX Placeholder: " + key + " (ID: " + targetId + ")");
                break;
            }
        }

        // 2. Fallback to standard baseNames
        if (!targetId) {
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
        }
        
        if (targetId) {
            if (i === 0) {
                selectLayerAM(targetId);
                var doc = app.activeDocument;
                var placeholder = doc.activeLayer; 
                placeAndAlign(doc, null, placeholder, file);
                if (colorLabel) setLayerLabelColorAM(doc.activeLayer.id, groupColor);
            }
        } else if (layerMap["_self"]) {
            try {
                selectLayerAM(layerMap["_self"]);
                var doc = app.activeDocument;
                var group = doc.activeLayer;
                var groupBounds = group.bounds;
                
                var idPlc = charIDToTypeID("Plc ");
                var desc = new ActionDescriptor();
                desc.putPath(charIDToTypeID("null"), file);
                executeAction(idPlc, desc, DialogModes.NO);
                
                var newLayer = doc.activeLayer;
                newLayer.name = imageName;
                if (colorLabel) setLayerLabelColorAM(newLayer.id, colorLabel);
                
                var nBounds = newLayer.bounds;
                var nWidth = nBounds[2].value - nBounds[0].value;
                var nHeight = nBounds[3].value - nBounds[1].value;
                
                var targetSize = 500;
                var scale = (targetSize / Math.max(nWidth, nHeight)) * 100;
                newLayer.resize(scale, scale, AnchorPosition.MIDDLECENTER);
                
                var gRight = groupBounds[2].value;
                var gTop = groupBounds[1].value;
                
                var currentBounds = newLayer.bounds;
                var dx = (gRight + 50 + (i * 550)) - currentBounds[0].value;
                var dy = (gTop + 50) - currentBounds[1].value;
                
                newLayer.translate(dx, dy);
                newLayer.move(group, ElementPlacement.PLACEAFTER);
                
                logToManifest("Placed standardized image " + imageName + " to the right of " + group.name);
            } catch(e) {
                logToManifest("Error placing image " + imageName + ": " + e);
            }
        }
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
    return app.activeDocument.activeLayer.id; 
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

// Helper: Process A4 Groups (Dynamic Generation based on JSON Order)
function processA4Groups(doc, plan, win) {
    var targets = [];
    var seen = {};
    
    for (var i=0; i<plan.actions.length; i++) {
        var grp = plan.actions[i].group;
        if (grp.indexOf("A4_Grp_") === 0) {
            if (!seen[grp]) {
                targets.push(grp);
                seen[grp] = true;
            }
        }
    }
    
    if (targets.length === 0) return false;
    
    logToManifest("A4 Groups Requested: " + targets.join(", "));
    
    var map = scanLayersAM();
    var templateId = null;
    var templateHeight = 0;
    
    if (map["A4_01"]) templateId = map["A4_01"]["_self"];
    if (!templateId && map["A4"]) templateId = map["A4"]["_self"];
    if (!templateId && map["A4_Grp_01"]) templateId = map["A4_Grp_01"]["_self"];
    
    if (!templateId) {
        logToManifest("CRITICAL: Template Group (A4_01 or A4) not found. Skipping A4 generation.");
        return false;
    }
    
    selectLayerAM(templateId);
    var bounds = app.activeDocument.activeLayer.bounds;
    templateHeight = bounds[3].value - bounds[1].value;
    
    var didChange = false;
    var padding = 100;
    
    for (var i=0; i<targets.length; i++) {
        var targetName = targets[i];
        if (map[targetName]) continue;
        
        if (win) {
            win.pnl.lblStatus.text = "Generating " + targetName + "...";
            win.update();
        }
        
        logToManifest("Generating " + targetName + " from Template...");
        selectLayerAM(templateId);
        var newGroupId = duplicateLayerAM(templateId);
        renameLayerAM(newGroupId, targetName);
        
        var offsetV = i * (templateHeight + padding);
        if (offsetV > 0) {
            translateLayerAM(newGroupId, 0, offsetV);
            logToManifest("Offsetting " + targetName + " by " + offsetV + "px");
        }
        
        var parts = targetName.split("_");
        var suffix = parts[2] || "XX";
        var activeGroup = app.activeDocument.activeLayer;
        
        (function recurse(layerObj, newIdx) {
             for (var k=0; k<layerObj.layers.length; k++) {
                 var child = layerObj.layers[k];
                 var oldName = child.name;
                 var cleanName = oldName.replace(/\s+copy\s*\d*$/i, "");
                 
                 // Smart Suffix Replacement (01 -> XX)
                 // Handles: _01,  01, : 01, :01
                 var suffixPatterns = ["_01", " 01", ": 01", ":01"];
                 var didReplace = false;
                 for (var s = 0; s < suffixPatterns.length; s++) {
                     if (cleanName.indexOf(suffixPatterns[s]) >= 0) {
                         var newSuffix = suffixPatterns[s].replace("01", newIdx);
                         cleanName = cleanName.replace(suffixPatterns[s], newSuffix);
                         didReplace = true;
                         break;
                     }
                 }

                 if (child.name !== cleanName) child.name = cleanName;
                 if (child.typename == "LayerSet") recurse(child, newIdx);
             }
        })(activeGroup, suffix);
        
        didChange = true;
    }
    
    if (didChange) setVisibleAM(templateId, false);
    
    return didChange;
}

function runBuild(doc, plan) {
    logToManifest("runBuild Started for Page " + plan.page);
    var total = plan.actions.length;
    
    var win = new Window("palette", "LetakMaster Builder");
    win.pnl = win.add("panel", [10, 10, 440, 100], "Building Page " + plan.page);
    win.pnl.progBar = win.pnl.add("progressbar", [20, 35, 410, 60], 0, total);
    win.pnl.lblStatus = win.pnl.add("statictext", [20, 20, 410, 35], "Scanning Document...");
    
    win.show();
    
    var isA4Mode = false;
    try {
        if (processA4Groups(doc, plan, win)) {
            logToManifest("A4 Structure Generated. Re-scanning...");
            isA4Mode = true;
        } else {
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

    if (isA4Mode) {
        logToManifest("A4 Mode Active: Hiding Standard Product Groups...");
        for (var i=1; i<=16; i++) {
            var suffix = (i < 10) ? "0" + i : "" + i;
            var variants = ["Product_" + suffix, "Product_" + suffix + "_K", "Product_" + suffix + "_EX"];
            for (var v=0; v<variants.length; v++) {
                var gName = variants[v];
                if (docMap[gName]) setVisibleAM(docMap[gName]["_self"], false);
            }
        }
    } else {
        logToManifest("Grid Mode Active: Hiding A4 Groups...");
        // 1. Hide explicit A4 placeholders and groups
        if (docMap["A4_01"]) setVisibleAM(docMap["A4_01"]["_self"], false);
        if (docMap["A4"]) setVisibleAM(docMap["A4"]["_self"], false);
        
        // 2. Hide any generated A4_Grp_XX
        for (var i=1; i<=10; i++) {
            var suffix = (i < 10) ? "0" + i : "" + i;
            var gName = "A4_Grp_" + suffix;
            if (docMap[gName]) setVisibleAM(docMap[gName]["_self"], false);
        }
    }

    // Standard Variants Hiding (Simplified for brevity as it was correct)
    function hideVariantsAM(currentGroupName, hero) {
        var id = parseInt(currentGroupName.replace("Product_", "").replace("A4_Grp_", ""), 10);
        if (currentGroupName.indexOf("Product_") === -1) return;
        
        var suffixId = (id < 10) ? "0" + id : "" + id;
        var variants = ["Product_" + suffixId, "Product_" + suffixId + "_K", "Product_" + suffixId + "_EX"];
        
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
    
    // Cycle Colors for Visual Clarity
    var colors = ["Red", "Orange", "Yellow", "Green", "Blue", "Violet", "Gray"];

    for (var i = 0; i < total; i++) {
        var action = plan.actions[i];
        var groupName = action.group;
        var targetGroup = groupName;
        
        // QOL: Highlight Color
        var groupColor = colors[i % colors.length];
        
        if (groupName === "A4_Grp_01" && !docMap[groupName] && docMap["A4_01"]) targetGroup = "A4_01";
        else if (groupName === "A4_Grp_01" && !docMap[groupName] && docMap["A4"]) targetGroup = "A4";
        
        logToManifest("Processing Action: " + groupName + " (Target: " + targetGroup + ")");
        
        if (i % 3 === 0 || i === total - 1) {
            win.pnl.progBar.value = i + 1;
            win.pnl.lblStatus.text = "Processing " + groupName + "...";
            win.update(); 
        }
        
        var groupLayers = docMap[targetGroup];
        if (!groupLayers) {
            logToManifest("WARNING: Group " + targetGroup + " not found in DocMap.");
            continue;
        }
        
        // Apply Color to Group
        if (groupLayers["_self"]) {
            setVisibleAM(groupLayers["_self"], true);
            setLayerLabelColorAM(groupLayers["_self"], groupColor);
        }
        
        try {
            if (targetGroup.indexOf("Product_") === 0) hideVariantsAM(targetGroup, action.hero);
            
            var shiftCandidates = {}; 
            var mainTitle = null; // Store title for renaming

            for (var key in action.data) {
                if (key.indexOf("image_") === 0) {
                    if (g_imagesDir) {
                        replaceProductImageAM(groupLayers, action.data[key], g_imagesDir, groupColor);
                    }
                } else {
                    var result = updateTextLayerAM(groupLayers, key, action.data[key]);
                    
                    // Capture Main Title for renaming
                    // Matches "nazev_XXA" or just "nazev_XX"
                    if (result && key.toLowerCase().indexOf("nazev_") >= 0) {
                        var parts = key.split("_");
                        var suffixChar = parts.length > 1 ? parts[1].slice(-1).toUpperCase() : "";
                        if (suffixChar === "A" || key.toLowerCase() === "nazev_" + parts[1]) {
                            mainTitle = result.text;
                        }
                    }
                    
                    if (result && key.toLowerCase().indexOf("nazev_") >= 0) {
                        var parts = key.split("_");
                        if (parts.length >= 2) {
                            var idPart = parts[1]; 
                            var lastChar = idPart.charAt(idPart.length - 1).toUpperCase();
                            var baseId = idPart.substring(0, idPart.length - 1);
                            
                            if (!shiftCandidates[baseId]) shiftCandidates[baseId] = { idA: null, textA: "", idB: null, textB: "" };
                            if (lastChar === "A") { shiftCandidates[baseId].idA = result.id; shiftCandidates[baseId].textA = result.text; }
                            else if (lastChar === "B") { shiftCandidates[baseId].idB = result.id; shiftCandidates[baseId].textB = result.text; }
                        }
                    }
                }
            }
            
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
                    var layerId = findLayerId(groupLayers, key);
                    if (layerId) {
                        logToManifest("Setting Visibility for " + key + " (ID: " + layerId + "): " + action.visibility[key]);
                        setVisibleAM(layerId, action.visibility[key]);
                    } else {
                        logToManifest("Failed to find layer for visibility: " + key);
                    }
                }
            }
            
            // QOL: Rename Group to Title
            if (mainTitle && groupLayers["_self"]) {
                // Ensure name is safe (max length, chars)
                var safeName = mainTitle.substring(0, 30).replace(/[:\/\\*?"<>|]/g, "");
                if (safeName.length > 0) {
                    logToManifest("Renaming " + targetGroup + " to " + safeName);
                    renameLayerAM(groupLayers["_self"], safeName);
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
