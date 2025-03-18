$(() => {
    console.log('ready?')
    segDir = '/imgs/1seg/'
    vecDir = '/imgs/2vec/'
    
    var scale = 0.25
    
    var matchId = 0
    var matchList = []
    var matchPage = 0

    var clearMatch = () => {
        matchId = 0
        matchList = []
        matchPage = 0
        $('#matches ul.list').html('')
        $('#match_id').text('')
        $('#match_weight').text('')
        $('#match_rotation').text('')
    }

    
    // init the canvas /
    var stage = createCanvas('canvas', 780, 780);
    var board = new Konva.Layer();
    stage.add(board); 
    
    fixed = {}
    $.getJSON('/api/fixed', (res) => {
        fixed = Object.assign(fixed, res)
        for (const i of Array(38).keys()) {
            for (const j of Array(40).keys()) {
                gridId = padZero(i) + padZero(j)
                dataId = ''
                dispId = ''
                className = 'piece'
                if (fixed[gridId]) {
                    dataId = fixed[gridId]
                    dispId = padZero(dataId, 4)
                    className += ' fixed'
                }
                $('#board').append(`<div id="${gridId}" data-id="${dataId}" class="${className}">${dataId}</div>`)
            }
        }
    })
    
    var cleanBoard = () => { clearEdges() && $('#pick').hide() }
    document.addEventListener('keydown', (e) => {
        if (e.key == 'Escape') 
            cleanBoard()
    })
    
    var padZero = (x, size = 2) => `${x}`.padStart(size, 0)
    
    // init the pick page
    var initPick = id => {
        board.removeChildren()
        var [x, y] = [id.substr(0,2), id.substr(2,2)]
        var [i, j] = [parseInt(x), parseInt(y)]
        let [u, d, l, r] = [i-1, i+1, j-1, j+1].map(a => padZero(a))
        let sur = [
            // [`${u}${l}`, `${u}${y}`, `${u}${r}`],
            // [`${x}${l}`, `${x}${y}`, `${x}${r}`],
            // [`${d}${l}`, `${d}${y}`, `${d}${r}`]
            [0, `${u}${y}`, 0],
            [`${x}${l}`, 0, `${x}${r}`],
            [0, `${d}${y}`, 0]
        ]
        sur.map((row, y) => {
            row.map((gid, x) => drawOnBoard(x, y, $(`#${gid}`).attr('data-id') || 0))
        })
        
        clearMatch()
        $('#board>div').removeClass('active')
        $(`#${id}`).addClass('active')
        $('#pick').css('display', 'flex')
    }
    
    var drawOnBoard = (x, y, pid) => {
        if (pid == 0) return
        drawPiece(parseInt(pid), x*260, y*260, scale, board)
    }
    
    var addToEdges = (id, edge) => {
        var dup = false
        $('ul.edges li').each((_, ele) => {
            if ($(ele)[0].id.startsWith(id))
                dup = true
        })
        if (dup) return
        if ($(`#${id}-${edge}`).length < 1) 
            $('ul.edges').append(`<li id="${id}-${edge}">piece ${id}, edge ${edge}</li>`)
    }
    
    var drawMatchList = (page) => {
        var size = 7
        if (page < 1 || (page-1) * size > matchList.length) return 
        matchPage = page
        data = matchList.slice((matchPage-1)*size, matchPage*size)
        $('#matches ul.list').html('').append(data.map((match) => {
            itemId = match[0]
            segImg = getSegImgUrl(itemId)
            return `<li><span>${itemId}</span><img title='${itemId}' data-id='${itemId}' src='${segImg}'></li>`
        }))
    }
    
    var findMatchList = () => {
        ids = []
        $('ul.edges li').each((_, e) => ids.push(e.id))
        if (ids.length < 1) return
        
        idStr = ids.join(',')
        $.getJSON(`/api/find/${idStr}`, (data) => {
            $('#matches ul.list').html('')
            matchList = data
            drawMatchList(1)
            destroyMatch()
        })
    }
    
    var clearEdges = () => $('ul.edges').html('')
    $('#close').on('click', cleanBoard)
    $('#clear').on('click', clearEdges)
    $('#find').on('click', findMatchList)
    
    $('#prev').on('click', () => drawMatchList(matchPage - 1))
    $('#next').on('click', () => drawMatchList(matchPage + 1))

    $('#confirm').on('click', () => {
        var pid = matchId
        var pos = $('#board>div.active')[0].id
        var deg = $('#match_rotation').text()
        if (pid < 1) return 
        $.getJSON(`/api/save_fit/${pid}/${pos}/${deg}`, (x) => {
            pid = padZero(pid)
            $(`#${pos}`).removeClass('active').addClass('fixed')
            $(`#${pos}`).attr('data-id', pid)
            $(`#${pos}`).html(padZero(pid, 4))
            clearEdges() && $('#pick').hide()
        }).fail(() => alert('failed!'))
    })
    
    board.on('dblclick', 'Group', function(evt) {
        var shape = evt.target;
        // var group = evt.currentTarget;
        shapeId = shape.id()
        if (shapeId.indexOf('-') > 0) {
            [pid, edge] = shapeId.split('-')
            addToEdges(pid, edge)
            findMatchList()
        }
        // console.log(shape, group)
    });
    
    var drawMatchInfo = () => {
        $('#match_id').text(matchId)
        matchList.map(m => {
            if (m[0] == matchId) {
                $('#match_weight').text(m[1])
            }
        })
    }
    
    var destroyMatch = () => {
        if (matchId > 0) {
            stage.find(`#label-${matchId}`)[0]?.destroy()
            stage.find(`#group-${matchId}`)[0]?.destroy()
            stage.find(`#control-${matchId}`)[0]?.destroy()
        } 
    }
    
    var drawMatch = async (e) => {
        destroyMatch()
        $('#matches ul.list li').removeClass('active')
        $(e.target).parent().addClass('active')
        
        matchId = $(e.target).attr('data-id')
        await drawPiece(matchId, 260, 260, scale, board, anchorFill = 'gold')
        drawMatchInfo()
        g = stage.findOne(`#group-${matchId}`)
        $('#match_rotation').text('0')
        g.on('transform', () => {
            $('#match_rotation').text(g.rotation().toFixed(2))
        })
    }
    
    
    
    // start to pick a piece
    $('#board').on('click', 'div', (e) => initPick($(e.target)[0].id))
    $('#matches ul.list').on('dblclick', 'img', (e) => drawMatch(e))
})