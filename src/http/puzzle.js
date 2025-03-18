$(function(){
    segDir = '/imgs/1seg/'
    vecDir = '/imgs/2vec/'
    var onBoards = [];

    // init Konva Stage, add board layer
    var stage = new Konva.Stage({
        container: 'canvas',
        width: 2000,
        height: 1900
    });
    var board = new Konva.Layer();
    stage.add(board);
    
    var getSegImg = (id) => {
        strId = id < 1000 ? `0${id}` : `${id}`
        a = strId.substr(0,2)
        b = strId.substr(2,2)
        return `${segDir}${a}-${b}.bmp`
    }
    
    var findMatches = (id, side) => {
        $.getJSON(`/api/matches/${id}/${side}`, (data) => {
            $('#matches ul').html('')
            data = data.slice(0, 12)
            list = data.map((match) => {
                matchId = match[0]
                segImg = getSegImg(matchId)
                return `<li><img title='${matchId}' data-id='${matchId}' src='${segImg}'></li>`
            });
    
            $('#matches ul').append(list)
        })
    }
    
    function addToBoard(id, data) {
        if (onBoards.includes(id)) 
            return ;

        Konva.Image.fromURL(getSegImg(id), (img) => {
            var piece = new Konva.Group({
                id: `g${id}`,
                x: 500,
                y: 200,
                draggable: true,
            });
            
            var nodes = [];
            img.setAttrs({threshold: 20})
                .cache().filters([Konva.Filters.Mask])
            nodes.push(img)

            tag = new Konva.Label({
                id: `t${id}`,
                x: 150,
                y: 150,
            });
            
            tag.add(new Konva.Tag({
                fill: 'yellow',
            }), new Konva.Text({
                text: id, 
                fontSize: 16,
                fill: 'red',
            }))
            
            // delete piece from board
            tag.on('dblclick', () => {
                if (confirm(`remove ${id}, You sure?`)) {
                    board.findOne(`#g${id}`).destroy()
                    board.findOne(`#c${id}`).destroy()
                    onBoards = onBoards.filter(i => i != id)
                }
            })

            // adding edge mid dots
            colors = ['red', 'green', 'blue', 'yellow']
            for (i in [0, 1, 2, 3]) {
                vts = data[i]['vertices']
                mid = vts[Math.floor(vts.length/2)]
                var dot = new Konva.Circle({
                    x: mid[0],
                    y: mid[1],
                    fill: colors[i],
                    radius: 10,
                })
                
                var cbMatch = (id, i) => () => findMatches(id, i)
                dot.on('dblclick', cbMatch(id, i))
                nodes.push(dot)
            }
            
            // adding piece center dot
            nodes.push(new Konva.Circle({
                x: data[0]['piece_center'][0], 
                y: data[0]['piece_center'][1],
                fill: 'black',
                radius: 20
            }), tag)
            piece.add(...nodes)
            board.add(piece, new Konva.Transformer({
                id: `c${id}`,   // control id
                nodes: [piece],
                anchorCornerRadius: 10,
                rotateAnchorCursor: 'move',
                rotateLineVisible: true,
                rotateAnchorOffset: 10,
                borderEnabled: false,
                resizeEnabled: false,
            }))
            onBoards.push(id)
        })
    }
    
    $('ul.pieces, #matches ul').on('click', 'li', (e) => {
        id = $(e.target).attr('data-id')
        if (onBoards.includes(id)) return
        $.getJSON(`api/vecpath/${id}`, (data) => {
            addToBoard(id, data)
        })
    })
    
    $.getJSON('/api/corners', function(data){
        list = data.map((id) => {
            segImg = getSegImg(id)
            return `<li><img title='${id}' data-id='${id}' src='${segImg}'></li>`
        });

        $('#corner .pieces').append(list)
    })

})