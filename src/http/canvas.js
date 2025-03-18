var createCanvas = (id, w, h) => {
    return new Konva.Stage({
        container: id,
        width: w,
        height: h
    })
}

var getSegImgUrl = (id) => {
    strId = id < 1000 ? `0${id}` : `${id}`
    a = strId.substr(0,2)
    b = strId.substr(2,2)
    return `${segDir}${a}-${b}.bmp`
}

// Top Left corner piece id label
var drawPieceLabel = (x, y, pid) => {
    return (new Konva.Label({
        id: `label-${pid}`,
        x: x+1,
        y: y+1,
    })).add(new Konva.Tag({fill: 'yellow'}), new Konva.Text({
        text: pid, 
        fontSize: 16
    }))
}

var drawEdgeDots = (pid, data) => {
    // adding edge mid dots
    var dots = [];
    let colors = ['red', 'green', 'blue', 'black'];
    [0, 1, 2, 3].map((i) => {
        vts = data[i]['vertices']
        mid = vts[Math.floor(vts.length/2)]
        dots.push(new Konva.Circle({
            id: `${pid}-${i}`,
            x: mid[0],
            y: mid[1],
            fill: colors[i],
            radius: 36,
        }))
    })

    // // adding piece center dot
    // dots.push(new Konva.Circle({
    //     x: data[0]['piece_center'][0], 
    //     y: data[0]['piece_center'][1],
    //     fill: 'black',
    //     radius: 20
    // }))
    
    return dots
}

var drawImgGroup = (x, y, img, pid, data, scale) => {
    var groupW = img.width() * scale
    var groupH = img.height() * scale
    var piece = new Konva.Group({
        id: `group-${pid}`,
        x: x+10,
        y: y+25,
        scale: {x:scale, y:scale},
        draggable: true,
    });
    piece.add(img.setAttrs({threshold: 20})
        .cache()
        .filters([Konva.Filters.Mask]))
    piece.add(...drawEdgeDots(pid, data))
    
    // rotate group
    $.getJSON(`api/rotation/${pid}`, r => {
        rotateAroundCenter(piece, groupW, groupH, r, scale)
    })
    return piece
}

var drawTransformer = (pid, node, anchorFill) => {
    return new Konva.Transformer({
        id: `control-${pid}`,   // control id
        nodes: [node],
        anchorCornerRadius: 10,
        anchorFill: anchorFill,
        rotateAnchorCursor: 'move',
        rotateLineVisible: true,
        rotateAnchorOffset: 10,
        borderEnabled: false,
        resizeEnabled: false,
    })
}

async function fetchData(pid) {
    return new Promise((resolve, reject) => {
        $.getJSON(`api/vecpath/${pid}`, (data) => {
            resolve(data)
        }, (err) => {
            reject(err)
        })
    });
}

async function drawPieceOnBoard(pid, x, y, scale, data, board, anchorFill) {
    return new Promise((resolve, _) => {
        Konva.Image.fromURL(getSegImgUrl(pid), (img) => {
            var piece = drawImgGroup(x, y, img, pid, data, scale)
            board.add(
                drawPieceLabel(x, y, pid),
                piece,
                drawTransformer(pid, piece, anchorFill)
            )
            resolve(true)
        })
    })
}

var drawPiece = async (pid, x, y, scale, board, anchorFill) => {
    var data = await fetchData(pid)
    await drawPieceOnBoard(pid, x, y, scale, data, board, anchorFill)
}

const rotatePoint = ({ x, y }, rad) => {
    const rcos = Math.cos(rad);
    const rsin = Math.sin(rad);
    return { x: x * rcos - y * rsin, y: y * rcos + x * rsin };
};

function rotateAroundCenter(node, w, h, rotation) {
    if (rotation == "0") return
    const topLeft = { x: -w / 2, y: -h / 2 };
    const current = rotatePoint(topLeft, Konva.getAngle(node.rotation()));
    const rotated = rotatePoint(topLeft, Konva.getAngle(rotation));
    const dx = rotated.x - current.x, dy = rotated.y - current.y;
    node.rotation(rotation);
    node.x(node.x() + dx);
    node.y(node.y() + dy);
}