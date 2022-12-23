GAMEBOARD_STOP_GAME_LOOP = false

class Game {
    constructor(canvasElement, htmlElement) {
        this.canvasElement = canvasElement
        this.ctx = this.canvasElement.getContext("2d")
        this.htmlElement = htmlElement
        this.gameboard = null
        this.previousGameTime = null
        this.entities = []
    }

    init(elapsedTime, callback) {
        this.previousGameTime = elapsedTime
        callback()
    }

    update(totalGameTime) {
        this.entities = this.entities.filter(entity => !entity.isDead())

        const elapsedTime = totalGameTime - this.previousGameTime
        this.previousGameTime = elapsedTime
        this.canvasElement.width = this.htmlElement.clientWidth
        this.canvasElement.height = this.htmlElement.clientHeight
        this.entities.forEach(entity => entity.update(elapsedTime))
    }

    draw() {
        this.ctx.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height)
        this.ctx.save()
        this.entities.forEach(entity => entity.draw(this.ctx))
        this.ctx.restore()
    }
}


class Position {
    constructor(x, y) {
        this.x = x
        this.y = y
    }
}


class Dimensions {
    constructor(width, height) {
        this.width = width
        this.height = height
    }
}


class Entity {
    constructor(position, dimensions, duration = null) {
        this.timeAlive = 0
        this.dead = false
        this.position = position
        this.dimensions = dimensions
        this.duration = duration
    }

    update(elapsedTime) {
        this.timeAlive += elapsedTime
        if (this.duration !== null && this.timeAlive > this.duration) {
            this.dead = true
        }
    }

    draw(ctx) {
        throw new Error("Not implemented")
    }

    isDead() {
        return this.dead
    }
}


class Tile extends Entity {
    constructor(position, dimensions, idleColor, highlightColor, flickerColor) {
        super(position, dimensions)
        // #fc9403
        this.idleColor = idleColor
        this.highlightColor = highlightColor
        this.flickerColor = flickerColor
    }

    update(elapsedTime) {
        super.update(elapsedTime)
    }

    draw(ctx, scaleFactor = 1) {
        ctx.fillStyle = this.idleColor
        ctx.fillRect(this.position.x, this.position.y, this.dimensions.width, this.dimensions.height)
    }
}


function startGame() {
    let game = null

    function main(totalSimTime, game) {
        if (!GAMEBOARD_STOP_GAME_LOOP) {
            window.requestAnimationFrame((totalSimTime) => {
                main(totalSimTime, game)
            })
        }
        game.update(totalSimTime)
        game.draw()
    }

    const canvasElement = document.querySelector("#gameboard-canvas")
    const htmlElement = document.querySelector("#gameboard")
    htmlElement.style.width = "100%"
    htmlElement.style.height = "100%"
    htmlElement.style.margin = "0"
    game = new Game(canvasElement, htmlElement)
    game.init(window.performance.now(), () => {
        window.requestAnimationFrame((totalSimTime) => {
            main(totalSimTime, game)
        })
    })
}


function kill() {
    GAMEBOARD_STOP_GAME_LOOP = true
}
