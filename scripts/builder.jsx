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
    // Adobe ExtendScript doesn't have native JSON.parse. 
    // Secure-ish eval for local trusted files.
    var obj = eval('(' + content + ')');
    logToManifest("JSON Parsed. Actions: " + (obj.actions ? obj.actions.length : "0"));
    return obj;
}

// Utility: Hide a Group
function hideGroup(doc, groupName) {
    try {
        var grp = doc.layerSets.getByName(groupName);
        grp.visible = false;
    } catch(e) {
        // Ignore if already gone
    }
}

// Utility: Resize/Mask Group (Simplified placeholder logic)
// In reality, this would modify the Vector Mask or specific "box" layer
function setGroupSize(doc, groupName, hero) {
    // This is complex in pure DOM. 
    // Usually involves selecting the "box" layer and transforming it.
    // For now, we assume the user has "Templates" or we simply don't resize 
    // but just allow the content to flow.
    // BUT, we MUST hide the overlapped groups.
    
    // Grid Logic (1-16)
    // 1  2  3  4
    // 5  6  7  8
    // 9  10 11 12
    // 13 14 15 16
    
    var id = parseInt(groupName.replace("Product_", ""), 10);
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
            hideGroup(doc, "Product_" + suffix);
        }
    }
}

var g_manifest = [];

function updateTextLayer(group, layerName, text) {
    logToManifest("Updating Text: " + group.name + " / " + layerName + " -> " + text);
    var status = "Missing";
    var method = "Direct";
    
    try {
        var layer = findLayerRecursive(group, layerName);
        
        // Fallback strategies for EAN/Labels
        if (!layer) {
            // Strategy 1: Try prefix before underscore (e.g. "EAN:_01" -> "EAN:")
            if (layerName.indexOf("_") > 0) {
                var prefix = layerName.split("_")[0];
                layer = findLayerRecursive(group, prefix);
                if (layer) method = "Fallback_Prefix_" + prefix;
            }
        }
        
        if (!layer && layerName.indexOf("EAN") >= 0) {
            // Strategy 2: Common EAN variations
            var vars = ["EAN", "EAN:", "EAN_label"];
            for (var i=0; i<vars.length; i++) {
                if (!layer) {
                    layer = findLayerRecursive(group, vars[i]);
                    if (layer) method = "Fallback_Var_" + vars[i];
                }
            }
        }

        if (layer) {
            if (layer.kind == LayerKind.TEXT) {
                layer.textItem.contents = text;
                status = "Updated";
                logToManifest("SUCCESS: Updated " + layer.name + " via " + method);
            } else {
                status = "WrongType_" + layer.kind;
                logToManifest("FAIL: Layer found but not TEXT. Type: " + layer.kind);
            }
        } else {
            logToManifest("FAIL: Layer NOT FOUND: " + layerName);
        }
    } catch(e) {
        status = "Error_" + e.message;
        logToManifest("ERROR in updateTextLayer: " + e);
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
        // simple data type
        if (t == "string") obj = '"' + obj.replace(/"/g, '\\"') + '"';
        return String(obj);
    } else {
        // recurse array or object
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
        // alert("Manifest saved to root!");
    } catch(e) {
        alert("Manifest SAVE ERROR: " + e);
    }
}

function findLayerRecursive(parent, name) {
    try {
        // Direct match first (fast)
        try {
            var layer = parent.layers.getByName(name);
            return layer;
        } catch(e) {
            // Proceed to loop
        }
        
        // Iterate for case-insensitive or recursive search
        for (var i = 0; i < parent.layers.length; i++) {
            var cur = parent.layers[i];
            
            // Check name case-insensitive
            if (cur.name.toLowerCase() === name.toLowerCase()) {
                return cur;
            }
            
            // Recurse if group
            if (cur.typename == "LayerSet") {
                var found = findLayerRecursive(cur, name);
                if (found) return found;
            }
        }
    } catch(e) {
        // General error
    }
    return null;
}

// --- Globals & Config ---
// These specific variables can be injected by the backend prepending to this script
var g_injected_json_dir = typeof g_injected_json_dir !== 'undefined' ? g_injected_json_dir : null;
var g_injected_images_dir = typeof g_injected_images_dir !== 'undefined' ? g_injected_images_dir : null;
var g_injected_automation = typeof g_injected_automation !== 'undefined' ? g_injected_automation : false;

var g_imagesDir = null;
var g_config = {};

function main() {
    logToManifest("Script Started");
    // Save User Preference
    var originalDisplayDialogs = app.displayDialogs;
    // Suppress all dialogs (including Missing Fonts)
    app.displayDialogs = DialogModes.NO;
    
    try {
        // 1. Priority: Injected Paths (Dynamic Run)
        if (g_injected_images_dir) {
            var d = new Folder(g_injected_images_dir);
            if (d.exists) {
                g_imagesDir = d;
            }
        }

        // 2. Fallback: Config File
        var scriptPath = File($.fileName).parent.fsName;
        var configFile = new File(scriptPath + "/config.json");
        if (configFile.exists && !g_imagesDir) {
            try {
                g_config = readJSON(configFile.fsName);
                if (g_config.images_dir) {
                    var d = new Folder(g_config.images_dir);
                    if (d.exists) g_imagesDir = d;
                }
            } catch(e) { }
        }

        var mode = "select"; // default
        
        if (app.documents.length > 0) {
            if (g_injected_automation) {
                // In automation mode, we prioritize active document without asking
                mode = "active";
            } else {
                // Temporarily re-enable dialogs just for this confirmation if needed, 
                // but since this is interactive, we can assume NO dialogs is fine for the confirm too?
                // No, confirm() works regardless of displayDialogs setting usually.
                var result = confirm("Process ACTIVE document '" + app.activeDocument.name + "'?\n\nClick YES to process Active Document.\nClick NO to Select Files from disk.");
                if (result) {
                    mode = "active";
                }
            }
        }
        
        logToManifest("Mode: " + mode);
        if (mode == "active") {
            processDocument(app.activeDocument);
        } else {
            // Select Files
            var files = File.openDialog("Select PSD Files to Automate", "*.psd", true);
            if (files && files.length > 0) {
                for (var i = 0; i < files.length; i++) {
                    var f = files[i];
                    var doc = open(f);
                    processDocument(doc);
                    // Optional: Save and Close?
                    // doc.save();
                    // doc.close();
                }
            }
        }
    } finally {
        // Restore User Preference
        app.displayDialogs = originalDisplayDialogs;
    }
}

function updateAllTextLayers() {
    try {
        var idupdateAllTextLayers = stringIDToTypeID( "updateAllTextLayers" );
        var desc = new ActionDescriptor();
        executeAction( idupdateAllTextLayers, desc, DialogModes.NO );
    } catch(e) {
        // Ignore if fails (e.g. no text layers or command not available)
    }
}

function processDocument(doc) {
    app.activeDocument = doc; // Focus
    
    // Force text engine to initialize to prevent "Missing Font" or "Update" dialogs/errors
    updateAllTextLayers();
    
    var docName = doc.name;
    
    // 1. Auto-Detect Page Number
    var pageNum = null;
    var match = docName.match(/Page\s*(\d+)/i);
    
    if (match && match[1]) {
        pageNum = parseInt(match[1], 10);
    }
    
    if (!pageNum || isNaN(pageNum)) {
        alert("Skipping '" + docName + "': Could not detect 'Page XX' in filename.");
        return;
    }
    
    // 2. Locate JSON Plan
    var docPath = doc.path;
    var jsonName = "build_page_" + pageNum + ".json";
    var scriptPath = File($.fileName).parent.fsName;
    var projectRoot = new Folder(scriptPath + "/.."); // Assuming scripts/ is in root
    
    var jsonFile = null;
    
    // Strategy Priority 0: Injected Dynamic Path
    if (g_injected_json_dir) {
        var d = new Folder(g_injected_json_dir);
        if (d.exists) {
             var f = new File(d.fsName + "/" + jsonName);
             if (f.exists) jsonFile = f;
        }
    }
    
    // Strategy Priority 1: Configured JSON Directory (Fallback)
    if (!jsonFile && g_config.json_dir) {
        var d = new Folder(g_config.json_dir);
        if (d.exists) {
             var f = new File(d.fsName + "/" + jsonName);
             if (f.exists) jsonFile = f;
        }
    }
    
    // Strategy Priority 2: Structured Workspace Plans (Latest)
    if (!jsonFile) {
        var plansRoot = new Folder(projectRoot.fsName + "/workspaces/build_plans");
        if (plansRoot.exists) {
            var stateFolders = plansRoot.getFiles("state_*");
            if (stateFolders.length > 0) {
                stateFolders.sort();
                var selectedFolder = stateFolders[stateFolders.length - 1]; // Latest
                if (selectedFolder) {
                    var potentialFile = new File(selectedFolder.fsName + "/" + jsonName);
                    if (potentialFile.exists) {
                        jsonFile = potentialFile;
                    }
                }
            }
        }
    }
    
    // Strategy Priority 3: Direct Adjacency (Legacy)
    if (!jsonFile) {
        var directPaths = [
            docPath + "/" + jsonName,
            scriptPath + "/" + jsonName,
            projectRoot.fsName + "/" + jsonName
        ];
        
        for (var i = 0; i < directPaths.length; i++) {
            var f = new File(directPaths[i]);
            if (f.exists) { jsonFile = f; break; }
        }
    }
    
    // Strategy Priority 4: Manual Selection
    if (!jsonFile) {
        alert("Could not auto-locate " + jsonName + ".\nPlease select the Build Plan JSON file manually.");
        jsonFile = File.openDialog("Select " + jsonName, "*.json");
    }
    
    if (!jsonFile) {
        alert("Aborted: No Build Plan selected.");
        return;
    }

    var plan = readJSON(jsonFile.fsName);

    // Ask for Image Directory if not yet set
    if (!g_imagesDir) {
        g_imagesDir = Folder.selectDialog("Select the directory containing Product Images");
    }
    
    // 3. Execute
    g_manifest = []; // Reset for this doc
    doc.suspendHistory("Build Page " + pageNum, "runBuild(doc, plan)");
    
    // 4. Save Manifest
    saveManifest(jsonFile.fsName, pageNum);
}

function runBuild(doc, plan) {
    logToManifest("runBuild Started for Page " + plan.page);
    var total = plan.actions.length;
    
    // Create Progress Window
    var win = new Window("palette", "LetakMaster Builder");
    win.pnl = win.add("panel", [10, 10, 440, 100], "Building Page " + plan.page);
    win.pnl.progBar = win.pnl.add("progressbar", [20, 35, 410, 60], 0, total);
    win.pnl.lblStatus = win.pnl.add("statictext", [20, 20, 410, 35], "Starting...");
    
    win.show();
    
    // Process Actions
    for (var i = 0; i < total; i++) {
        var action = plan.actions[i];
        var groupName = action.group;
        
        // Update Progress
        win.pnl.progBar.value = i + 1;
        win.pnl.lblStatus.text = "Processing " + groupName + " (" + (i + 1) + "/" + total + ")...";
        win.update(); // Force redraw
        
        try {
            var group = doc.layerSets.getByName(groupName);
            group.visible = true; // Ensure active group is visible
            
            // Handle Overlap Hiding
            setGroupSize(doc, groupName, action.hero);
            
            // DEBUG: Log all data keys
            var dataKeys = [];
            for (var k in action.data) dataKeys.push(k);
            logToManifest("Data Keys for " + groupName + ": " + dataKeys.join(", "));
            
            // Update Text & Images
            for (var key in action.data) {
                if (key.indexOf("image_") === 0) {
                    // Handle Image Replacement
                    if (g_imagesDir) {
                        replaceProductImage(group, action.data[key], g_imagesDir);
                    }
                } else {
                    updateTextLayer(group, key, action.data[key]);
                }
            }
            
            // Handle Visibility (Explicit Toggles)
            if (action.visibility) {
                for (var key in action.visibility) {
                    toggleLayerVisibility(group, key, action.visibility[key]);
                }
            }
            
        } catch(e) {
            // Group might not exist
        }
    }
    
    win.close();
    // alert("Page " + plan.page + " Built Successfully!");
}

function toggleLayerVisibility(group, layerName, isVisible) {
    try {
        var layer = findLayerRecursive(group, layerName);
        if (layer) {
            layer.visible = isVisible;
        }
    } catch(e) {
        // Ignore if layer not found
    }
}

function findImageFile(dir, basename) {
    var extensions = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".psd", ".webp"];
    
    // Check exact match first
    var f = new File(dir.fsName + "/" + basename);
    if (f.exists) return f;
    
    // Check extensions
    for (var i = 0; i < extensions.length; i++) {
        f = new File(dir.fsName + "/" + basename + extensions[i]);
        if (f.exists) return f;
        // Also check uppercase ext
        f = new File(dir.fsName + "/" + basename + extensions[i].toUpperCase());
        if (f.exists) return f;
    }
    return null;
}

function replaceProductImage(group, imageName, imageDir) {
    // DEBUG: Check what we are looking for
    // alert("Looking for image: '" + imageName + "' in " + imageDir.fsName);

    // 1. Resolve File
    var file = findImageFile(imageDir, imageName);
    if (!file) {
        // alert("Image NOT found: " + imageName);
        return;
    }
    
    // 2. Find Placeholder (Try common names: "image", "obraz", "photo", "packshot")
    // We also support suffix matching if the JSON key implies it, but here we just look for standard placeholders.
    var targetLayer = findLayerRecursive(group, "image");
    if (!targetLayer) targetLayer = findLayerRecursive(group, "obraz");
    if (!targetLayer) targetLayer = findLayerRecursive(group, "photo");
    if (!targetLayer) targetLayer = findLayerRecursive(group, "packshot");
    
    // Fallback: Try finding layer containing "obraz" or "image" loosely
    if (!targetLayer) {
        for (var i=0; i<group.layers.length; i++) {
             var nm = group.layers[i].name.toLowerCase();
             if (nm.indexOf("obraz") >= 0 || nm.indexOf("image") >= 0) {
                 targetLayer = group.layers[i];
                 break;
             }
        }
    }
    
    if (targetLayer) {
        // Use Place & Hide Strategy
        placeAndAlign(app.activeDocument, group, targetLayer, file);
    }
}

function placeAndAlign(doc, group, placeholder, file) {
    try {
        // 1. Get Bounds of Placeholder
        var bounds = placeholder.bounds; // [left, top, right, bottom]
        var pLeft = bounds[0].value;
        var pTop = bounds[1].value;
        var pRight = bounds[2].value;
        var pBottom = bounds[3].value;
        
        var pWidth = pRight - pLeft;
        var pHeight = pBottom - pTop;
        var pCenterX = pLeft + (pWidth / 2);
        var pCenterY = pTop + (pHeight / 2);

        // 2. Select the Placeholder so Place puts it above
        doc.activeLayer = placeholder;
        
        // 3. Place Image
        var idPlc = charIDToTypeID("Plc ");
        var desc = new ActionDescriptor();
        var idnull = charIDToTypeID("null");
        desc.putPath(idnull, file);
        var idFTcs = charIDToTypeID("FTcs");
        var idQCSt = charIDToTypeID("QCSt");
        var idQcsa = charIDToTypeID("Qcsa");
        desc.putEnumerated(idFTcs, idQCSt, idQcsa); // Place as Smart Object if possible
        executeAction(idPlc, desc, DialogModes.NO);
        
        var newLayer = doc.activeLayer;
        
        // 4. Resize to Fit (Contain)
        var nBounds = newLayer.bounds;
        var nWidth = nBounds[2].value - nBounds[0].value;
        var nHeight = nBounds[3].value - nBounds[1].value;
        
        // Avoid div by zero
        if (nWidth > 0 && nHeight > 0) {
            var wRatio = pWidth / nWidth;
            var hRatio = pHeight / nHeight;
            
            // Contain strategy: use smaller ratio
            var scale = Math.min(wRatio, hRatio) * 100;
            
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
        
        // 6. Hide Placeholder
        placeholder.visible = false;
        
    } catch(e) {
        // alert("Place & Align failed: " + e);
    }
}

main();
