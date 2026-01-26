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
    file.open('r');
    var content = file.read();
    file.close();
    var obj = eval('(' + content + ')');
    logToManifest("JSON Parsed. Actions: " + (obj.actions ? obj.actions.length : "0"));
    return obj;
}

// Utility: Hide a Group (Optimized using cache)
function hideGroupOptimized(doc, groupName, groupIndex) {
    var grp = groupIndex[groupName];
    if (grp) {
        grp.visible = false;
    }
}

// Utility: Resize/Mask Group (Optimized)
function setGroupSizeOptimized(doc, groupName, hero, groupIndex) {
    var id = parseInt(groupName.replace("Product_", ""), 10);
    var suffixId = (id < 10) ? "0" + id : "" + id;

    // Enforce Exclusive Visibility: Hide all other variants of this slot
    // We check the Index first to avoid slow DOM calls for non-existent groups
    var variants = [
        "Product_" + suffixId, 
        "Product_" + suffixId + "_K", 
        "Product_" + suffixId + "_EX"
    ];
    
    for (var v = 0; v < variants.length; v++) {
        var vName = variants[v];
        if (vName != groupName) {
            hideGroupOptimized(doc, vName, groupIndex);
        }
    }
    
    // Hide overlapped slots based on Hero size
    var toHide = [];
    if (hero == 2) {
        // Vertical: Hide ID + 4
        toHide.push(id + 4);
    } else if (hero == 4) {
        // 2x2: Hide ID+1, ID+4, ID+5
        toHide.push(id + 1);
        toHide.push(id + 4);
        toHide.push(id + 5);
    }
    
    for (var i = 0; i < toHide.length; i++) {
        var hideId = toHide[i];
        if (hideId <= 16) {
            var suffix = (hideId < 10) ? "0" + hideId : "" + hideId;
            var base = "Product_" + suffix;
            // Also hide variants of the overlapped slot!
            hideGroupOptimized(doc, base, groupIndex);
            hideGroupOptimized(doc, base + "_K", groupIndex);
            hideGroupOptimized(doc, base + "_EX", groupIndex);
        }
    }
}

var g_manifest = [];

// Recursive Map Builder: Returns { "lowercase_name": LayerObject }
function mapLayers(parent, map) {
    if (!map) map = {};
    
    for (var i = 0; i < parent.layers.length; i++) {
        var layer = parent.layers[i];
        var nameKey = layer.name.toLowerCase();
        
        // Store first match only (standard behavior)
        if (!map[nameKey]) {
            map[nameKey] = layer;
        }
        
        // Recurse if group
        if (layer.typename == "LayerSet") {
            mapLayers(layer, map);
        }
    }
    return map;
}

function updateTextLayerCached(group, layerName, text, layerMap) {
    var status = "Missing";
    var method = "Direct";
    var layer = null;
    
    try {
        // 1. Direct Lookup
        layer = layerMap[layerName.toLowerCase()];
        
        // 2. Fallback: Suffix "K" / "EX" (Underscore)
        if (!layer) {
            var groupParts = group.name.split("_");
            if (groupParts.length > 2) {
                var ext = groupParts[groupParts.length - 1]; // "K" or "EX"
                var altName = layerName + "_" + ext;
                layer = layerMap[altName.toLowerCase()];
                if (layer) method = "Fallback_Suffix_" + ext;
            }
        }
        
        // 3. Fallback: Suffix "K" / "EX" (No Underscore)
        if (!layer) {
            var groupParts = group.name.split("_");
            if (groupParts.length > 2) {
                var ext = groupParts[groupParts.length - 1];
                var altName = layerName + ext;
                layer = layerMap[altName.toLowerCase()];
                if (layer) method = "Fallback_Suffix_NoUnderscore_" + ext;
            }
        }

        // 4. Fallback: EAN Variations
        if (!layer) {
             // Prefix (EAN:_01 -> EAN:)
             if (layerName.indexOf("_") > 0) {
                var prefix = layerName.split("_")[0];
                layer = layerMap[prefix.toLowerCase()];
                if (layer) method = "Fallback_Prefix_" + prefix;
             }
        }
        
        if (!layer && layerName.indexOf("EAN") >= 0) {
            var vars = ["EAN", "EAN:", "EAN_label"];
            for (var i=0; i<vars.length; i++) {
                if (!layer) {
                    layer = layerMap[vars[i].toLowerCase()];
                    if (layer) method = "Fallback_Var_" + vars[i];
                }
            }
        }

        if (layer) {
            if (layer.kind == LayerKind.TEXT) {
                layer.textItem.contents = text;
                status = "Updated";
            } else {
                status = "WrongType_" + layer.kind;
            }
        }
    } catch(e) {
        status = "Error_" + e.message;
    }
    
    g_manifest.push({
        "group": group.name,
        "layer": layerName,
        "action": "Text",
        "value": text,
        "status": status,
        "method": method
    });
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

function main() {
    logToManifest("Script Started");
    var originalDisplayDialogs = app.displayDialogs;
    app.displayDialogs = DialogModes.NO;
    
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

function runBuild(doc, plan) {
    logToManifest("runBuild Started for Page " + plan.page);
    var total = plan.actions.length;
    
    var win = new Window("palette", "LetakMaster Builder");
    win.pnl = win.add("panel", [10, 10, 440, 100], "Building Page " + plan.page);
    win.pnl.progBar = win.pnl.add("progressbar", [20, 35, 410, 60], 0, total);
    win.pnl.lblStatus = win.pnl.add("statictext", [20, 20, 410, 35], "Starting...");
    
    win.show();
    
    // --- OPTIMIZATION: Index all Groups once ---
    logToManifest("Indexing Groups...");
    var groupIndex = {};
    for (var i = 0; i < doc.layerSets.length; i++) {
        groupIndex[doc.layerSets[i].name] = doc.layerSets[i];
    }
    
    for (var i = 0; i < total; i++) {
        var action = plan.actions[i];
        var groupName = action.group;
        
        // Throttled UI Update (Every 3 items)
        if (i % 3 === 0 || i === total - 1) {
            win.pnl.progBar.value = i + 1;
            win.pnl.lblStatus.text = "Processing " + groupName + " (" + (i + 1) + "/" + total + ")...";
            win.update(); 
        }
        
        // Fast Lookup
        var group = groupIndex[groupName];
        if (!group) continue;
        
        try {
            group.visible = true; 
            
            // Optimized Visibility Handling
            setGroupSizeOptimized(doc, groupName, action.hero, groupIndex);
            
            // --- OPTIMIZATION: Map Group Layers once ---
            var layerMap = mapLayers(group);
            
            // Update Text
            for (var key in action.data) {
                if (key.indexOf("image_") === 0) {
                    if (g_imagesDir) {
                        replaceProductImageCached(group, action.data[key], g_imagesDir, layerMap);
                    }
                } else {
                    updateTextLayerCached(group, key, action.data[key], layerMap);
                }
            }
            
            // Update Visibility
            if (action.visibility) {
                for (var key in action.visibility) {
                    var layer = layerMap[key.toLowerCase()];
                    if (layer) layer.visible = action.visibility[key];
                }
            }
            
        } catch(e) {
            logToManifest("Error processing group " + groupName + ": " + e);
        }
    }
    
    win.close();
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

function replaceProductImageCached(group, imageName, imageDir, layerMap) {
    var file = findImageFile(imageDir, imageName);
    if (!file) return;
    
    var baseNames = ["image", "obraz", "photo", "packshot"];
    var targetLayer = null;
    
    var groupParts = group.name.split("_");
    var ext = (groupParts.length > 2) ? groupParts[groupParts.length - 1] : null;

    for (var i = 0; i < baseNames.length; i++) {
        var bName = baseNames[i];
        
        // 1. Direct
        targetLayer = layerMap[bName.toLowerCase()];
        if (targetLayer) break;
        
        // 2. Suffix
        if (ext) {
            targetLayer = layerMap[(bName + "_" + ext).toLowerCase()];
            if (targetLayer) break;
            targetLayer = layerMap[(bName + ext).toLowerCase()];
            if (targetLayer) break;
        }
    }
    
    if (!targetLayer) {
        // Fallback: Scan map keys for "obraz"/"image"
        for (var key in layerMap) {
             if (key.indexOf("obraz") >= 0 || key.indexOf("image") >= 0) {
                 targetLayer = layerMap[key];
                 break;
             }
        }
    }
    
    if (targetLayer) {
        placeAndAlign(app.activeDocument, group, targetLayer, file);
    }
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
        
        // 4. Resize to Fit (Contain)
        // "Cant be larger than template image in any dimension" -> standard Fit/Contain.
        
        var nBounds = newLayer.bounds;
        var nWidth = nBounds[2].value - nBounds[0].value;
        var nHeight = nBounds[3].value - nBounds[1].value;
        
        // Avoid div by zero
        if (nWidth > 0 && nHeight > 0) {
            var wRatio = pWidth / nWidth;
            var hRatio = pHeight / nHeight;
            
            // "Contain" strategy: use the smaller ratio to ensure BOTH dimensions fit within the box.
            // This ensures the image is never larger than the placeholder in any dimension.
            // Example: Image 1000x1000, Box 500x200. wRatio=0.5, hRatio=0.2. Scale=20%. Result 200x200. Fits in 500x200.
            var scale = Math.min(wRatio, hRatio) * 100;
            
            // Optional: If you NEVER want to scale UP small images (only shrink large ones), uncomment this:
            // if (scale > 100) scale = 100; 
            
            newLayer.resize(scale, scale, AnchorPosition.MIDDLECENTER);
        }
        
        // 5. Center Align
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

main();