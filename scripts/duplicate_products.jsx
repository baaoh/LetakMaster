// duplicate_products.jsx
// Run this script in Adobe Photoshop

// #target photoshop

function main() {
    if (app.documents.length === 0) {
        alert("Please open the PSD file first.");
        return;
    }

    var doc = app.activeDocument;
    var sourceGroupName = "Product_01";
    var totalProducts = 16;

    // Find the source group
    var sourceGroup = null;
    try {
        sourceGroup = doc.layerSets.getByName(sourceGroupName);
    } catch (e) {
        alert("Group '" + sourceGroupName + "' not found!");
        return;
    }

    // Create a progress bar window
    var win = new Window("palette", "Processing Products", undefined);
    win.pbar = win.add("progressbar", undefined, 0, totalProducts - 1);
    win.pbar.preferredSize.width = 300;
    win.stext = win.add("statictext", undefined, "Starting...");
    win.stext.preferredSize.width = 300;
    win.center();
    win.show();

    function processDuplication() {
        for (var i = 2; i <= totalProducts; i++) {
            // Update progress bar
            win.pbar.value = i - 1;
            win.stext.text = "Creating Product " + i + " of " + totalProducts + "...";
            win.update(); // Force UI update

            var suffix = (i < 10) ? "0" + i : "" + i; // Pad with zero
            var oldSuffix = "01";
            
            // Duplicate the group
            var newGroup = sourceGroup.duplicate(sourceGroup, ElementPlacement.PLACEBEFORE);
            
            // Explicitly set the name to remove " copy"
            newGroup.name = "Product_" + suffix;

            // Rename contents recursively
            renameLayers(newGroup, "_"+oldSuffix, "_"+suffix);
        }
        win.close();
    }

    // Run the process
    processDuplication();

    function renameLayers(parent, findStr, replaceStr) {
        for (var j = 0; j < parent.layers.length; j++) {
            var layer = parent.layers[j];
            
            // 1. Remove " copy" artifacts first
            // Matches " copy", " copy 2", " copy 10" at the end of string
            var cleanName = layer.name.replace(/ copy\s*\d*$/i, "");
            if (layer.name !== cleanName) {
                layer.name = cleanName;
            }

            // 2. Perform the specific suffix replacement (e.g., _01 -> _02)
            // Using a global regex to ensure we catch it wherever it is (though usually once)
            if (layer.name.indexOf(findStr) !== -1) {
                // Construct a Regex for safer replacement if needed, 
                // but simple string replace is usually sufficient for this structure.
                // We use split/join idiom for global replacement in older JS engines if needed,
                // but standard replace works for the first occurrence which is typical here.
                layer.name = layer.name.split(findStr).join(replaceStr);
            }

            // 3. Recurse if it is a Group (LayerSet)
            if (layer.typename == "LayerSet") {
                renameLayers(layer, findStr, replaceStr);
            }
        }
    }

    alert("Created " + (totalProducts - 1) + " new product groups.");
}

main();
