var g_injected_images_dir = "D:/TAMDA/LetakMaster/workspaces/images";
var g_injected_json_dir = "D:/TAMDA/LetakMaster/workspaces/build_plans/Workspace_State_16.xlsx_2026-01-24_00-51-58";
var g_injected_automation = true;
#target photoshop

// Utility: Read JSON
function readJSON(filePath) {
    var file = new File(filePath);
    file.open('r');
    var content = file.read();
    file.close();
    // Adobe ExtendScript doesn't have native JSON.parse. 
    // Secure-ish eval for local trusted files.
    return eval('(' + content + ')');
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

function updateTextLayer(group, layerName, text) {
    try {
        // Recurse finding layer? Or assume flat structure?
        // Our schema verification showed layers are nested deep (Pricetag_XX/cena_XX...)
        // We need a recursive finder.
        var layer = findLayerRecursive(group, layerName);
        if (layer && layer.kind == LayerKind.TEXT) {
            layer.textItem.contents = text;
        }
    } catch(e) {
        // alert("Error updating " + layerName + ": " + e);
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
            var result = confirm("Process ACTIVE document '" + app.activeDocument.name + "'?\n\nClick YES to process Active Document.\nClick NO to Select Files from disk.");
            if (result) {
                mode = "active";
            }
        }
    }
    
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
}

function processDocument(doc) {
    app.activeDocument = doc; // Focus
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
    doc.suspendHistory("Build Page " + pageNum, "runBuild(doc, plan)");
}

function runBuild(doc, plan) {
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
    alert("Page " + plan.page + " Built Successfully!");
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
    // 1. Resolve File
    var file = findImageFile(imageDir, imageName);
    if (!file) {
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
