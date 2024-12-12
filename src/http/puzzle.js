$(function(){
    segDir = '/imgs/1seg/'
    vecDir = '/imgs/2vec/'

    function getSegImg(id) {
        strId = String(id)
        a = strId.substr(0,2)
        b = strId.substr(2,2)
        return `${segDir}${a}-${b}.bmp`
    }

    function addToCanvas(id) {
        fabric.FabricImage.fromURL(getSegImg(id))
            .then((img) => {
                canvas.add(img)
                onBoards.append(id)
            })
    }

    function getVecImg(id) {
        strId = String(id)
        a = strId.substr(0,2)
        b = strId.substr(2,2)
        return `${vecDir}${parseInt(a)}${b}_${a}-${b}.svg`
    }
    
    $('ul.pieces').on('click', 'li', (e) => {
        id = $(e.target).attr('data-id')
        addToCanvas(id)
    })

    $.getJSON('/api/corners', function(data){
        list = data.map((id) => {
            segImg = getSegImg(id)
            return `<li><img data-id='${id}' src='${segImg}'></li>`
        });

        $('#corner .pieces').append(list)
    })
    
    const canvas = new fabric.StaticCanvas('canvas')
    var onBoards = [];

})