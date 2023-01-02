const NewGameBoard = function (gameBoardData, canvasElement) {
    let GAMEBOARD_STOP_GAME_LOOP = false
    let board = null
    const TILE_IDLE_COLOR = "#eb8934"
    const TILE_HIGHLIGHT_COLOR = "#ffb778"
    const TILE_FLICKER_COLOR = "#ffffff"
    const TILE_LABEL_COLOR = "#a8d7e0"
    const TILE_FONT = "bold 72px Lora"
    const CATEGORY_FONT = "bold 40px Lora"
    const REFERENCE_RESOLUTION_WIDTH = 1920
    const REFERENCE_RESOLUTION_HEIGHT = 1080

    let DEBUG_FLAG = false

    let gameEntities = []

    class Game {
        constructor(canvasElement) {
            this.canvasElement = canvasElement
            this.ctx = this.canvasElement.getContext("2d")
            this.previousGameTime = null
        }

        init(elapsedTime, callback) {
            this.previousGameTime = elapsedTime
            callback()
        }

        update(totalGameTime) {
            gameEntities = gameEntities.filter(entity => !entity.isDead())

            const elapsedTime = totalGameTime - this.previousGameTime
            this.previousGameTime = totalGameTime

            this.canvasElement.width = window.innerWidth
            this.canvasElement.height = 9 * window.innerWidth / 16
            this.scaleFactor = this.canvasElement.width / REFERENCE_RESOLUTION_WIDTH

            gameEntities.sort((a, b) => a.drawOrder - b.drawOrder)
            gameEntities.forEach(entity => entity.update(elapsedTime, this.canvasElement))
        }

        draw() {
            this.ctx.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height)
            this.ctx.save()
            gameEntities.forEach(entity => entity.draw(this.ctx, this.canvasElement, this.scaleFactor))
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
            this.drawOrder = 1
        }

        update(elapsedTime) {
            this.timeAlive += elapsedTime
            if (this.duration !== null && this.timeAlive > this.duration) {
                this.dead = true
            }
        }

        draw(ctx, canvasElement) {
            throw new Error("Not implemented")
        }

        isDead() {
            return this.dead
        }
    }


    class Tile extends Entity {
        constructor(
            position,
            dimensions,
            answer,
            question,
            category,
            label,
            labelPrefix,
            labelFont,
            labelColor,
            idleColor,
            highlightColor,
            flickerColor,
        ) {
            super(position, dimensions)

            this.state = "DOLLAR_AMOUNT"

            this.answer = answer
            this.question = question

            this.category = category
            this.label = label
            this.labelPrefix = labelPrefix
            this.labelFont = labelFont
            this.labelColor = labelColor
            this.idleColor = idleColor
            this.highlightColor = highlightColor
            this.flickerColor = flickerColor

            this.currentColor = this.idleColor
            this.flickerCount = 0
            this.flickerInterval = 200
            this.flickerTime = 0
            this.nextFlicker = 0
        }

        setHighlight() {
            this.currentColor = this.highlightColor
        }

        unsetHighlight() {
            this.currentColor = this.idleColor
        }

        flicker(onFlickerEnd) {
            this.flickerCount = 6
            this.flickerTime = 0
            this.nextFlicker = this.flickerInterval
            this.flickerStartColor = this.currentColor
            setTimeout(() => {
                onFlickerEnd()
            }, this.flickerCount * this.flickerInterval)

        }

        reveal() {
            this.state = "ANSWER"
            this.drawOrder = 5
        }

        markAnswered() {
            this.state = "ANSWERED"
            this.drawOrder = 1
        }

        update(elapsedTime) {
            super.update(elapsedTime)

            if (this.flickerCount > 0) {
                this.flickerTime += elapsedTime
                if (this.flickerTime > this.nextFlicker) {
                    this.nextFlicker += this.flickerInterval
                    this.flickerCount -= 1
                    if (this.currentColor === this.flickerStartColor) {
                        this.currentColor = this.flickerColor
                    } else {
                        this.currentColor = this.flickerStartColor
                    }
                }
            }
        }

        draw(ctx, canvasElement, scaleFactor) {
            if (this.state === "DOLLAR_AMOUNT") {
                this.drawDollarLabel(ctx, canvasElement, scaleFactor)
            } else if (this.state === "ANSWER") {
                this.drawAnswer(ctx, canvasElement, scaleFactor)
            } else {
                this.drawAnswered(ctx, canvasElement, scaleFactor)
            }
        }

        drawDollarLabel(ctx, _, scaleFactor) {
            ctx.fillStyle = this.currentColor
            ctx.fillRect(
                this.position.x,
                this.position.y,
                this.dimensions.width,
                this.dimensions.height
            )

            ctx.scale(scaleFactor, scaleFactor)

            const label = this.labelPrefix + this.label
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.font = this.labelFont

            ctx.fillStyle = "#000000"
            ctx.fillText(
                label,
                (this.position.x + (this.dimensions.width / 2) + 2) / scaleFactor,
                (this.position.y + (this.dimensions.height / 2) + 2) / scaleFactor
            )

            ctx.fillStyle = this.labelColor
            ctx.fillText(
                label,
                (this.position.x + (this.dimensions.width / 2)) / scaleFactor,
                (this.position.y + (this.dimensions.height / 2)) / scaleFactor
            )

            ctx.setTransform(1, 0, 0, 1, 0, 0)
        }

        drawAnswer(ctx, canvasElement, scaleFactor) {
            this.position.x = 0
            this.position.y = 0
            this.dimensions.width = canvasElement.width
            this.dimensions.height = canvasElement.height

            ctx.fillStyle = this.currentColor
            ctx.fillRect(
                this.position.x,
                this.position.y,
                this.dimensions.width,
                this.dimensions.height
            )

            ctx.scale(scaleFactor, scaleFactor)

            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.font = "bold 120px " + this.labelFont

            const maxWidth = this.dimensions.width * 0.95
            const words = this.answer.split(" ")

            const lines = []
            let nextWord = null
            let line = ""
            let newLineWidth = -1;
            for (let i = 0; i < words.length; i++) {
                nextWord = words[i]
                newLineWidth = ctx.measureText(line + " " + nextWord).width
                if (newLineWidth > maxWidth || i === words.length - 1) {
                    lines.push(line)
                    line = ""
                }
                line += " " + nextWord
                if (i === words.length - 1) {
                    lines.push(line)
                }
            }

            const fontMetrics = ctx.measureText("I")
            const yIncrement = fontMetrics.actualBoundingBoxAscent + fontMetrics.actualBoundingBoxDescent

            const drawLines = (offset) => {
                if (lines.length > 1) {
                    let mid = (() => {
                        if (lines.length % 2 === 0) {
                            return lines.length / 2
                        } else {
                            return Math.ceil(lines.length / 2)
                        }
                    })()
                    let yOffset = yIncrement * -mid
                    for (let line of lines) {
                        ctx.fillText(
                            line,
                            (this.position.x + (this.dimensions.width / 2) + offset) / scaleFactor,
                            (this.position.y + yOffset + (this.dimensions.height / 2) + offset) / scaleFactor
                        )
                        yOffset += yIncrement
                    }
                }
            }

            ctx.fillStyle = "#000000"
            drawLines(0)
            ctx.fillStyle = this.labelColor
            drawLines(2)

            ctx.setTransform(1, 0, 0, 1, 0, 0)
        }

        drawAnswered(ctx, canvasElement, scaleFactor) {
            ctx.fillStyle = this.currentColor
            ctx.fillRect(
                this.position.x,
                this.position.y,
                this.dimensions.width,
                this.dimensions.height
            )
        }
    }


    class Board extends Entity {
        constructor(boardData, position, dimensions) {
            super(position, dimensions)
            this.gameBoard = boardData
            this.currentRound = 0
        }

        startNextRound() {
            const round = this.gameBoard.rounds[this.currentRound]
            const numCols = round.categories.length
            const numRows = Object.keys(round.categories[0].questions).length + 1
            const tileWidth = this.dimensions.width / numCols
            const tileHeight = this.dimensions.height / numRows

            this.tiles = Array.from(Array(numCols), () => new Array(numRows));

            let xOffset = 0
            let col = 0
            for (let category of round.categories) {
                let yOffset = 0
                let row = 0
                let categoryTile = new Tile(
                    new Position(xOffset, yOffset),
                    new Dimensions(tileWidth, tileHeight),
                    null,
                    null,
                    category.name,
                    category.name,
                    "",
                    CATEGORY_FONT,
                    TILE_LABEL_COLOR,
                    TILE_IDLE_COLOR,
                    TILE_HIGHLIGHT_COLOR,
                    TILE_FLICKER_COLOR,
                    null
                )
                this.tiles[col][row] = categoryTile
                gameEntities.push(categoryTile)
                row += 1
                yOffset += tileHeight
                for (const [label, question] of Object.entries(category.questions)) {
                    console.log(label, question)
                    let tile = new Tile(
                        new Position(xOffset, yOffset),
                        new Dimensions(tileWidth, tileHeight),
                        question.answer,
                        question.question,
                        category.name,
                        label,
                        "$",
                        TILE_FONT,
                        TILE_LABEL_COLOR,
                        TILE_IDLE_COLOR,
                        TILE_HIGHLIGHT_COLOR,
                        TILE_FLICKER_COLOR,
                    )
                    this.tiles[col][row] = tile
                    gameEntities.push(tile)
                    yOffset += tileHeight
                    row += 1
                }
                xOffset += tileWidth
                col += 1
            }
        }

        setColumnHighlight(col) {
            for (let row in this.tiles[col]) {
                this.tiles[col][row].setHighlight()
            }
        }

        unsetColumnHighlight(col) {
            for (let row in this.tiles[col]) {
                this.tiles[col][row].unsetHighlight()
            }
        }

        update(elapsedTime, canvasElement) {
            this.dimensions.width = canvasElement.width
            this.dimensions.height = canvasElement.height

            let xOffset = 0
            for (let col in this.tiles) {
                let yOffset = 0
                for (let row in this.tiles[col]) {
                    this.tiles[col][row].position.x = xOffset
                    this.tiles[col][row].position.y = yOffset

                    this.tiles[col][row].dimensions.width = this.dimensions.width / this.tiles.length
                    this.tiles[col][row].dimensions.height = this.dimensions.height / this.tiles[col].length

                    yOffset += this.dimensions.height / this.tiles[col].length
                }
                xOffset += this.dimensions.width / this.tiles.length
            }
        }

        draw(ctx, canvasElement) {
            // tiles draw themselves. no need to do anything here
        }
    }


    (function () {
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

        game = new Game(canvasElement)
        game.init(window.performance.now(), () => {
            window.requestAnimationFrame((totalSimTime) => {
                board = new Board(
                    gameBoardData,
                    new Position(0, 0),
                    new Dimensions(canvasElement.width, canvasElement.height)
                )
                gameEntities.push(board)
                board.startNextRound()
                main(totalSimTime, game)
            })
        })
    })();


    function categoryToColumn(category) {
        for (let i = 0; i < board.tiles.length; i++) {
            if (board.tiles[i][0].category === category) {
                return i
            }
        }
    }


    function answerToRow(col, amount) {
        for (let j = 0; j < board.tiles[col].length; j++) {
            if (board.tiles[col][j].label === amount) {
                return j
            }
        }
    }


    return {
        setCategoryHighlight: function (category) {
            let col = categoryToColumn(category)
            board.setColumnHighlight(col)
        },
        unsetCategoryHighlight: function (category) {
            let col = categoryToColumn(category)
            board.unsetColumnHighlight(col)
        },
        flickerAnswer: function (category, amount, onFlickerEnd) {
            let col = categoryToColumn(category)
            let row = answerToRow(col, amount)
            board.tiles[col][row].flicker(() => {
                onFlickerEnd(col, row)
            })
        },
        // unrevealAnswer: function (category, amount) {
        //     let col = categoryToColumn(category)
        //     let row = answerToRow(col, amount)
        //     board.tiles[col][row].unreveal()
        // },
        markAnswered: function (category, amount) {
            let col = categoryToColumn(category)
            let row = answerToRow(col, amount)
            board.tiles[col][row].markAnswered()
        },
        setColumnHighlight: function (col) {
            board.setColumnHighlight(col)
        },
        unsetColumnHighlight: function (col) {
            board.unsetColumnHighlight(col)
        },
        flickerTile: function (col, row) {
            board.tiles[col][row].flicker()
        },
        revealAnswer: function (col, row) {
            board.tiles[col][row].reveal()
        },
        isAnswerUsed: function (col, row) {
            return board.tiles[col][row].state === "USED"
        },
        startNextRound: function () {
            board.startNextRound()
        },
        currentRound: function () {
            return board.currentRound
        },
        kill: function () {
            GAMEBOARD_STOP_GAME_LOOP = true
        },
        toggleDebugFlag: function () {
            DEBUG_FLAG = !DEBUG_FLAG
        }
    }
}
