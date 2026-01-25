#target photoshop

function main() {
    if (app.documents.length == 0) {
        alert("Please open a document with a placeholder layer named 'placeholder' first.");
        return;
    }
    
    var doc = app.activeDocument;
    var group = doc.activeLayer.parent; // Assume we are selecting something inside the group
    if (doc.activeLayer.typename == "LayerSet") group = doc.activeLayer;
    
    // Test Image
    var imageFile = File.openDialog("Select an image to place");
    if (!imageFile) return;

    // 1. Find Placeholder
    var placeholder = findLayer(group, "image");
    if (!placeholder) placeholder = findLayer(group, "obraz");
    if (!placeholder) {
        alert("Could not find layer 'image' or 'obraz' in active group.");
        return;
    }
    
    // 2. Place & Align
    placeAndAlign(doc, group, placeholder, imageFile);
}

function findLayer(parent, namePartial) {
    for (var i = 0; i < parent.layers.length; i++) {
        var layer = parent.layers[i];
        if (layer.name.toLowerCase().indexOf(namePartial.toLowerCase()) >= 0) {
            return layer;
        }
    }
    return null;
}

function placeAndAlign(doc, group, placeholder, file) {
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

    // 2. Select the Group (so Place puts it inside/above)
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
    
    // Calculate Ratios
    var wRatio = pWidth / nWidth;
    var hRatio = pHeight / nHeight;
    
    // Use smaller ratio to 'Contain', larger to 'Cover'
    var scale = Math.min(wRatio, hRatio) * 100; // Percent
    
    newLayer.resize(scale, scale, AnchorPosition.MIDDLECENTER);
    
    // 5. Center Align
    // Recalculate bounds after resize
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
}

main();
