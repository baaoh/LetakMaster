#target photoshop
var g_injected_images_dir = "D:/TAMDA/LetakMaster-dev/workspaces/images";
var g_injected_json_dir = "D:/TAMDA/LetakMaster/workspaces/build_plans/260218_2322_Workspace_State_1.xlsx_State_1";
var g_injected_automation = true;

var scriptFolder = new File($.fileName).parent;
var projectRoot = scriptFolder.parent;
var LOG_FILE = new File(projectRoot.fsName + "/debug_manifest.txt");

function logToManifest(msg) {
    try {
        LOG_FILE.open('a');
        LOG_FILE.writeln(new Date().toTimeString() + ": " + msg);
        LOG_FILE.close();
    } catch(e) {}
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

// Helper: Set Text Content by ID
function setTextAM(layerId, text) {
    try {
        selectLayerAM(layerId);
        var doc = app.activeDocument;
        if (doc.activeLayer.kind == LayerKind.TEXT) {
             doc.activeLayer.textItem.contents = text;
        }
    } catch(e) {
        logToManifest("SetText Error (ID " + layerId + "): " + e);
    }
}

// Helper: Set Visibility by ID
function setVisibleAM(id, visible) {
    try {
        var desc = new ActionDescriptor();
        var list = new ActionList();
        var ref = new ActionReference();
        ref.putIdentifier(charIDToTypeID("Lyr "), id);
        list.putReference(ref);
        desc.putList(charIDToTypeID("null"), list);
        executeAction(stringIDToTypeID(visible ? "show" : "hide"), desc, DialogModes.NO);
    } catch(e) { 
        logToManifest("Visibility Error (ID " + id + "): " + e);
    }
}

// Helper: Scan All Layers via ActionManager
function scanLayersAM() {
    var map = {}; 
    try {
        var ref = new ActionReference();
        ref.putProperty(charIDToTypeID("Prpr"), charIDToTypeID("NmbL"));
        ref.putEnumerated(charIDToTypeID("Dcmn"), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        var count = executeActionGet(ref).getInteger(charIDToTypeID("NmbL"));
        
        logToManifest("AM Scan: Found " + count + " layers.");
        var stack = [];
        // Top-down traversal: count down to 1.
        for (var i = count; i >= 1; i--) {
            var layerRef = new ActionReference();
            layerRef.putIndex(charIDToTypeID("Lyr "), i);
            var layerDesc = executeActionGet(layerRef);
            
            var id = layerDesc.getInteger(charIDToTypeID("LyrI"));
            var name = layerDesc.getString(charIDToTypeID("Nm  "));
            var type = "content";
            
            if (layerDesc.hasKey(stringIDToTypeID("layerSection"))) {
                var ls = typeIDToStringID(layerDesc.getEnumerationValue(stringIDToTypeID("layerSection")));
                // AM: layerSectionEnd is the TOP (header), layerSectionStart is the BOTTOM (tail).
                if (ls == "layerSectionEnd") type = "groupStart";
                else if (ls == "layerSectionStart") type = "groupEnd";
            }
            
            if (type == "groupStart") {
                var isProduct = (name.indexOf("Product_") === 0 || name.indexOf("A4_") === 0);
                var entry = { name: name, isProduct: isProduct, id: id, flatChildren: {} };
                if (isProduct) {
                    map[name] = entry.flatChildren;
                    map[name]["_self"] = id; 
                    logToManifest("AM Map: Group Found [" + name + "] (ID " + id + ")");
                }
                stack.push(entry);
            } else if (type == "groupEnd") {
                if (stack.length > 0) stack.pop();
            } else {
                for (var s = stack.length - 1; s >= 0; s--) {
                    if (stack[s].isProduct) {
                        stack[s].flatChildren[name.toLowerCase()] = id;
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

// Helper: Title Case Converter
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
    var lowerSearch = layerName.toLowerCase();
    
    // 1. Direct and normalized variants
    function check(name) {
        if (layerIdMap[name]) return layerIdMap[name];
        var alts = [
            name.replace(/_/g, " "),
            name.replace(/ /g, "_"),
            name.replace(/:/g, ""),
            name.replace(/:/g, "_"),
            name.replace(/:/g, " ")
        ];
        for (var i=0; i<alts.length; i++) {
            var n = alts[i].replace(/\s+/g, " ").replace(/^\s+|\s+$/g, "");
            if (layerIdMap[n]) return layerIdMap[n];
        }
        return null;
    }

    var id = check(lowerSearch);
    if (id) return id;

    // 2. Regex match for "fuzzy" suffix/prefix
    var baseNameMatch = lowerSearch.match(/^([a-z\-]+)/i);
    var suffixMatch = lowerSearch.match(/(\d+.*)$/);
    
    if (baseNameMatch && suffixMatch) {
        var base = baseNameMatch[1];
        var suffix = suffixMatch[1];
        var patternStr = "^" + base + ".*" + suffix.replace(/[_ ]/g, ".*");
        var rx = new RegExp(patternStr, "i");
        
        for (var key in layerIdMap) {
            if (rx.test(key)) {
                logToManifest("Fuzzy Match Success: [" + layerName + "] -> [" + key + "]");
                return layerIdMap[key];
            }
        }
    }

    // 3. Last Resort: Alphanumeric normalization
    var normSearch = lowerSearch.replace(/[^a-z0-9]/g, "");
    for (var key in layerIdMap) {
        if (key.replace(/[^a-z0-9]/g, "") === normSearch) {
            logToManifest("Alphanumeric Match Success: [" + layerName + "] -> [" + key + "]");
            return layerIdMap[key];
        }
    }

    logToManifest("Search Failed for [" + layerName + "]. Available: " + (function(){
        var keys = []; for(var k in layerIdMap) if(k!="_self") keys.push(k); return keys.join(", ");
    })());

    return null;
}

// Helper: Update Text using ID Map
function updateTextLayerAM(layerIdMap, layerName, text) {
    var layerId = findLayerId(layerIdMap, layerName);
    if (layerId) {
        var safeText = text.toString();
        if (layerName.toLowerCase().indexOf("nazev") >= 0 && layerName.toUpperCase().indexOf("A") >= 0) {
            if (safeText === safeText.toUpperCase() && safeText.length > 2) {
                safeText = formatTitleCase(safeText);
            }
        }
        safeText = safeText.replace(/\\n/g, "\r").replace(/\r\n/g, "\r").replace(/\n/g, "\r");
        setTextAM(layerId, safeText);
        return { id: layerId, text: safeText };
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
        var pCenterX = (bounds[0].value + bounds[2].value) / 2;
        var pCenterY = (bounds[1].value + bounds[3].value) / 2;
        var pWidth = bounds[2].value - bounds[0].value;
        var pHeight = bounds[3].value - bounds[1].value;

        doc.activeLayer = placeholder;
        
        var idPlc = charIDToTypeID("Plc ");
        var desc = new ActionDescriptor();
        desc.putPath(charIDToTypeID("null"), file);
        desc.putEnumerated(charIDToTypeID("FTcs"), charIDToTypeID("QCSt"), charIDToTypeID("Qcsa")); 
        executeAction(idPlc, desc, DialogModes.NO);
        
        var newLayer = doc.activeLayer;
        var nBounds = newLayer.bounds;
        var nWidth = nBounds[2].value - nBounds[0].value;
        var nHeight = nBounds[3].value - nBounds[1].value;
        
        if (nWidth > 0 && nHeight > 0) {
            var scale = Math.min(pWidth / nWidth, pHeight / nHeight) * 100;
            newLayer.resize(scale, scale, AnchorPosition.MIDDLECENTER);
        }
        
        nBounds = newLayer.bounds;
        var nCenterX = (nBounds[0].value + nBounds[2].value) / 2;
        var nCenterY = (nBounds[1].value + nBounds[3].value) / 2;
        newLayer.translate(pCenterX - nCenterX, pCenterY - nCenterY);
        
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
    } catch(e) { }
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
        if (!file) continue;
        
        var targetId = null;
        for (var key in layerMap) {
            if (key == "_self") continue;
            if (key.indexOf(exPlaceholderBase) >= 0) {
                targetId = layerMap[key];
                break;
            }
        }

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
                placeAndAlign(app.activeDocument, null, app.activeDocument.activeLayer, file);
                if (colorLabel) setLayerLabelColorAM(app.activeDocument.activeLayer.id, colorLabel);
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
                
                var targetSize = 500;
                var scale = (targetSize / Math.max(newLayer.bounds[2].value - newLayer.bounds[0].value, newLayer.bounds[3].value - newLayer.bounds[1].value)) * 100;
                newLayer.resize(scale, scale, AnchorPosition.MIDDLECENTER);
                
                var dx = (groupBounds[2].value + 50 + (i * 550)) - newLayer.bounds[0].value;
                var dy = (groupBounds[1].value + 50) - newLayer.bounds[1].value;
                
                newLayer.translate(dx, dy);
                newLayer.move(group, ElementPlacement.PLACEAFTER);
            } catch(e) { }
        }
    }
}

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

// Helper: Translate Layer by ID
function translateLayerAM(id, dx, dy) {
    selectLayerAM(id);
    app.activeDocument.activeLayer.translate(dx, dy);
}

// Helper: Process A4 Groups
function processA4Groups(doc, plan, win) {
    var targets = [];
    var seen = {};
    for (var i=0; i<plan.actions.length; i++) {
        var grp = plan.actions[i].group;
        if (grp.indexOf("A4_Grp_") === 0) {
            if (!seen[grp]) { targets.push(grp); seen[grp] = true; }
        }
    }
    if (targets.length === 0) return false;
    
    var map = scanLayersAM();
    var templateId = map["A4_01"] ? map["A4_01"]["_self"] : (map["A4"] ? map["A4"]["_self"] : null);
    if (!templateId) return false;
    
    selectLayerAM(templateId);
    var templateHeight = app.activeDocument.activeLayer.bounds[3].value - app.activeDocument.activeLayer.bounds[1].value;
    var padding = 100;
    
    for (var i=0; i<targets.length; i++) {
        var targetName = targets[i];
        if (map[targetName]) continue;
        if (win) { win.pnl.lblStatus.text = "Generating " + targetName + "..."; win.update(); }
        
        selectLayerAM(templateId);
        var newGroupId = duplicateLayerAM(templateId);
        renameLayerAM(newGroupId, targetName);
        if (i > 0) translateLayerAM(newGroupId, 0, i * (templateHeight + padding));
        
        var suffix = targetName.split("_")[2] || "XX";
        (function recurse(layerObj, newIdx) {
             for (var k=0; k<layerObj.layers.length; k++) {
                 var child = layerObj.layers[k];
                 var cleanName = child.name.replace(/\s+copy\s*\d*$/i, "");
                 var suffixPatterns = ["_01", " 01", ": 01", ":01"];
                 for (var s = 0; s < suffixPatterns.length; s++) {
                     if (cleanName.indexOf(suffixPatterns[s]) >= 0) {
                         cleanName = cleanName.replace(suffixPatterns[s], suffixPatterns[s].replace("01", newIdx));
                         break;
                     }
                 }
                 if (child.name !== cleanName) child.name = cleanName;
                 if (child.typename == "LayerSet") recurse(child, newIdx);
             }
        })(app.activeDocument.activeLayer, suffix);
    }
    setVisibleAM(templateId, false);
    return true;
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
    try { isA4Mode = processA4Groups(doc, plan, win); } catch(e) {}
    
    logToManifest("Scanning Layers AM...");
    var docMap = scanLayersAM();
    
    function getGroup(name) {
        if (docMap[name]) return docMap[name];
        var low = name.toLowerCase();
        for (var key in docMap) if (key.toLowerCase() === low) return docMap[key];
        return null;
    }

    if (isA4Mode) {
        for (var i=1; i<=16; i++) {
            var s = (i < 10) ? "0" + i : "" + i;
            var vars = ["Product_" + s, "Product_" + s + "_K", "Product_" + s + "_EX"];
            for (var v=0; v<vars.length; v++) {
                var g = getGroup(vars[v]);
                if (g) setVisibleAM(g["_self"], false);
            }
        }
    } else {
        var a4_tags = ["A4_01", "A4"];
        for(var t=0; t<a4_tags.length; t++){
            var g = getGroup(a4_tags[t]); if(g) setVisibleAM(g["_self"], false);
        }
        for (var i=1; i<=10; i++) {
            var g = getGroup("A4_Grp_" + ((i < 10) ? "0" + i : i));
            if (g) setVisibleAM(g["_self"], false);
        }
    }

    var colors = ["Red", "Orange", "Yellow", "Green", "Blue", "Violet", "Gray"];
    for (var i = 0; i < total; i++) {
        var action = plan.actions[i];
        var groupName = action.group;
        var groupColor = colors[i % colors.length];
        
        var targetGroup = groupName;
        if (groupName === "A4_Grp_01" && !getGroup(groupName)) {
            targetGroup = getGroup("A4_01") ? "A4_01" : (getGroup("A4") ? "A4" : groupName);
        }
        
        logToManifest("Processing Action: " + groupName);
        win.pnl.progBar.value = i + 1;
        win.pnl.lblStatus.text = "Processing " + groupName + "...";
        win.update(); 
        
        var groupLayers = getGroup(targetGroup);
        if (!groupLayers) { logToManifest("Group Not Found: " + targetGroup); continue; }
        
        if (groupLayers["_self"]) {
            setVisibleAM(groupLayers["_self"], true);
            setLayerLabelColorAM(groupLayers["_self"], groupColor);
        }
        
        for (var key in action.data) {
            if (key.indexOf("image_") === 0) {
                if (g_imagesDir) replaceProductImageAM(groupLayers, action.data[key], g_imagesDir, groupColor);
            } else {
                updateTextLayerAM(groupLayers, key, action.data[key]);
            }
        }
        
        if (action.visibility) {
            for (var key in action.visibility) {
                var layerId = findLayerId(groupLayers, key);
                if (layerId) setVisibleAM(layerId, action.visibility[key]);
            }
        }
    }
    win.close();
}

function main() {
    var originalDisplayDialogs = app.displayDialogs;
    app.displayDialogs = DialogModes.NO;
    var originalRulerUnits = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;
    
    try {
        if (g_injected_images_dir) {
            var d = new Folder(g_injected_images_dir);
            if (d.exists) g_imagesDir = d;
        }
        
        var mode = (app.documents.length > 0 && g_injected_automation) ? "active" : "select";
        if (mode == "active") {
            processDocument(app.activeDocument);
        } else {
            var files = File.openDialog("Select PSD Files to Automate", "*.psd", true);
            if (files) {
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

function processDocument(doc) {
    app.activeDocument = doc;
    var pageNum = null;
    var match = doc.name.match(/Page\s*(\d+)/i);
    if (match) pageNum = parseInt(match[1], 10);
    if (!pageNum) return;
    
    var jsonName = "build_page_" + pageNum + ".json";
    var jsonFile = null;
    
    if (g_injected_json_dir) {
        var f = new File(g_injected_json_dir + "/" + jsonName);
        if (f.exists) jsonFile = f;
    }
    
    if (!jsonFile) {
        jsonFile = File.openDialog("Select " + jsonName, "*.json");
    }
    
    if (!jsonFile) return;
    var plan = readJSON(jsonFile.fsName);
    if (!g_imagesDir) g_imagesDir = Folder.selectDialog("Select Product Images");
    
    doc.suspendHistory("Build Page " + pageNum, "runBuild(doc, plan)");
}

main();