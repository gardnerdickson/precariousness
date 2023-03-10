const NewGameBoard = function (gameBoardData, playersState, canvasElement, onClueReveal, onClueExpired) {
    let GAMEBOARD_STOP_GAME_LOOP = false
    let board = null
    let statusBar = null
    const TILE_IDLE_COLOR = "#4c566a"
    const TILE_HIGHLIGHT_COLOR = "#81a1c1"
    const TILE_FLICKER_COLOR = "#ffffff"
    const TILE_LABEL_COLOR = "#ebcb8b"
    const TILE_FONT_SIZE = "72"
    const TILE_FONT = "Angkor"
    const TILE_BORDER_COLOR = "#ffffff"
    const TILE_BORDER_SIZE_PERCENTAGE = 0.0001
    const CATEGORY_FONT_SIZE = "26"
    const CATEGORY_FONT = "Angkor"
    const STATUS_FONT = "50px Angkor"
    const TIME_BAR_DURATION = 20000
    const REFERENCE_RESOLUTION_WIDTH = 1920
    const TEXT_SHADOW_OFFSET = 5

    let DEBUG_FLAG = false

    let gameEntities = []


    function lerp(start, end, amount) {
        return (1 - amount) * start + amount * end
    }


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

        area() {
            return this.width * this.height
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
            board,
            clue,
            categoryKey,
            label,
            labelPrefix,
            labelFont,
            labelFontSize,
            labelColor,
            idleColor,
            highlightColor,
            flickerColor,
            onClueReveal
        ) {
            super(position, dimensions)
            this.board = board

            this.state = "DOLLAR_AMOUNT"

            this.clue = clue

            this.categoryKey = categoryKey
            this.label = label
            this.labelPrefix = labelPrefix
            this.labelFont = labelFont
            this.labelFontSize = labelFontSize
            this.labelColor = labelColor
            this.idleColor = idleColor
            this.highlightColor = highlightColor
            this.flickerColor = flickerColor
            this.onClueReveal = onClueReveal

            this.currentColor = this.idleColor
            this.flickerCount = 0
            this.flickerInterval = 0
            this.flickerTime = 0
            this.nextFlicker = 0
        }

        setHighlight() {
            this.currentColor = this.highlightColor
        }

        unsetHighlight() {
            this.currentColor = this.idleColor
        }

        flicker(count, interval) {
            this.flickerCount = count
            this.flickerTime = 0
            this.nextFlicker = interval
            this.flickerInterval = interval
            this.flickerStartColor = this.currentColor
        }

        reveal() {
            this.state = "CLUE"
            this.drawOrder = 5
            this.onClueReveal(this.categoryKey, this.label)
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

        _drawBorder(ctx) {
            ctx.fillStyle = TILE_BORDER_COLOR
            ctx.fillRect(
                this.position.x,
                this.position.y,
                this.dimensions.width,
                this.dimensions.height
            )
        }

        _drawFill(ctx) {
            ctx.fillStyle = this.currentColor

            const borderSize = this.dimensions.area() * TILE_BORDER_SIZE_PERCENTAGE

            const width = this.dimensions.width - borderSize
            const height = this.dimensions.height - borderSize
            const xPos = this.position.x + (borderSize / 2)
            const yPos = this.position.y + (borderSize / 2)

            ctx.fillRect(xPos, yPos, width, height)
        }

        _drawLines(ctx, text, fontSize, offset, scaleFactor) {
            const maxWidth = this.dimensions.width * 0.95
            const words = text.toUpperCase().split(" ")

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
            const fontMetrics = ctx.measureText("H")
            const fontHeight = fontMetrics.actualBoundingBoxAscent + fontMetrics.actualBoundingBoxDescent

            const yIncrement = (fontHeight * scaleFactor) + (fontSize * 0.75 * scaleFactor)

            if (lines.length > 1) {
                let mid = (() => {
                    if (lines.length % 2 === 0) {
                        return lines.length / 2
                    } else {
                        return Math.floor(lines.length / 2)
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

        draw(ctx, canvasElement, scaleFactor) {
            if (this.state === "DOLLAR_AMOUNT") {
                this.drawLabel(ctx, canvasElement, scaleFactor)
            } else if (this.state === "CLUE") {
                this.drawClue(ctx, canvasElement, scaleFactor)
            } else {
                this.drawAnswered(ctx, canvasElement, scaleFactor)
            }
        }

        drawLabel(ctx, _, scaleFactor) {
            this._drawBorder(ctx)
            this._drawFill(ctx)

            ctx.scale(scaleFactor, scaleFactor)

            const label = this.labelPrefix + this.label
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.font = this.labelFontSize + "px " + this.labelFont

            ctx.fillStyle = "#000000"
            this._drawLines(ctx, label, this.labelFontSize, TEXT_SHADOW_OFFSET * scaleFactor, scaleFactor)

            ctx.fillStyle = this.labelColor
            this._drawLines(ctx, label, this.labelFontSize, 0, scaleFactor)

            ctx.setTransform(1, 0, 0, 1, 0, 0)
        }

        drawClue(ctx, canvasElement, scaleFactor) {
            this.position.x = 0
            this.position.y = 0
            this.dimensions.width = canvasElement.width * this.board.widthPercentage
            this.dimensions.height = canvasElement.height * this.board.heightPercentage

            this._drawBorder(ctx)
            this._drawFill(ctx)

            ctx.scale(scaleFactor, scaleFactor)

            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.font = this.labelFontSize + "px " + this.labelFont

            ctx.fillStyle = "#000000"
            this._drawLines(ctx, this.clue, this.labelFontSize, TEXT_SHADOW_OFFSET * scaleFactor, scaleFactor)
            ctx.fillStyle = this.labelColor
            this._drawLines(ctx, this.clue, this.labelFontSize, 0, scaleFactor)

            ctx.setTransform(1, 0, 0, 1, 0, 0)
        }

        drawAnswered(ctx, canvasElement, scaleFactor) {
            this._drawBorder(ctx)
            this._drawFill(ctx)
        }
    }


    class Board extends Entity {
        constructor(boardData, canvasElement, widthPercentage, heightPercentage) {
            super(
                new Position(0, 0),
                new Dimensions(canvasElement.width, canvasElement.height * heightPercentage)
            )
            this.gameBoard = boardData
            this.currentRound = boardData.currentRound
            this.widthPercentage = widthPercentage
            this.heightPercentage = heightPercentage

            const round = this.gameBoard.rounds[this.currentRound]
            const numCols = Object.keys(round).length
            const numRows = Object.keys(round[0].tiles).length + 1
            const tileWidth = (canvasElement.width * this.widthPercentage) / numCols
            const tileHeight = (canvasElement.height * this.heightPercentage) / numRows

            this.tiles = Array.from(Array(numCols), () => new Array(numRows));

            let xOffset = 0
            let col = 0
            for (let category of round) {
                let yOffset = 0
                let row = 0
                let categoryTile = new Tile(
                    new Position(xOffset, yOffset),
                    new Dimensions(tileWidth, tileHeight),
                    this,
                    null,
                    category.key,
                    category.name,
                    "",
                    CATEGORY_FONT,
                    CATEGORY_FONT_SIZE,
                    TILE_LABEL_COLOR,
                    TILE_IDLE_COLOR,
                    TILE_HIGHLIGHT_COLOR,
                    TILE_FLICKER_COLOR,
                    onClueReveal
                )
                this.tiles[col][row] = categoryTile
                gameEntities.push(categoryTile)
                row += 1
                yOffset += tileHeight
                for (const [label, tileClue] of Object.entries(category.tiles)) {
                    let tile = new Tile(
                        new Position(xOffset, yOffset),
                        new Dimensions(tileWidth, tileHeight),
                        this,
                        tileClue.clue,
                        category.key,
                        label,
                        "$",
                        TILE_FONT,
                        TILE_FONT_SIZE,
                        TILE_LABEL_COLOR,
                        TILE_IDLE_COLOR,
                        TILE_HIGHLIGHT_COLOR,
                        TILE_FLICKER_COLOR,
                        onClueReveal
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
            this.dimensions.width = canvasElement.width * this.widthPercentage
            this.dimensions.height = canvasElement.height * this.heightPercentage

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


    class StatusBar extends Entity {
        constructor(players, canvasElement, widthPercentage, heightPercentage) {
            super(
                new Position(0, canvasElement.height - (canvasElement * heightPercentage)),
                new Dimensions(canvasElement.width * widthPercentage, canvasElement.height * heightPercentage)
            )
            this.players = players
            this.widthPercentage = widthPercentage
            this.heightPercentage = heightPercentage
            this.font = STATUS_FONT
            this.displayTimeBar = false
            this.timeBarPaused = false
            this.timeBarElapsed = -1
            this.timeBarDuration = -1
            this.onTimeBarFinished = null
        }

        startTimeBar(duration, onTimeBarFinished) {
            this.displayTimeBar = true
            this.timeBarPaused = false
            this.timeBarDuration = duration
            this.timeBarElapsed = 0
            this.timeBarFinished = onTimeBarFinished
        }

        pauseTimeBar() {
            this.timeBarPaused = true
        }

        resumeTimeBar() {
            this.timeBarPaused = false
        }

        resetTimeBar() {
            this.displayTimeBar = false
        }

        update(elapsedTime, canvasElement) {
            this.dimensions.width = canvasElement.width * this.widthPercentage
            this.dimensions.height = canvasElement.height * this.heightPercentage
            this.position.x = 0
            this.position.y = canvasElement.height - (canvasElement.height * this.heightPercentage)

            if (this.displayTimeBar && !this.timeBarPaused) {
                this.timeBarElapsed += elapsedTime
                if (this.timeBarElapsed > this.timeBarDuration) {
                    this.displayTimeBar = false
                    if (this.timeBarFinished !== null) {
                        this.timeBarFinished()
                        this.timeBarFinished = null
                    }
                }
            }
        }

        draw(ctx, canvasElement, scaleFactor) {
            ctx.fillStyle = "#000000"
            ctx.fillRect(
                this.position.x,
                this.position.y,
                this.dimensions.width,
                this.dimensions.height
            )

            ctx.fillStyle = "#ffffff"
            const borderSize = this.dimensions.area() * TILE_BORDER_SIZE_PERCENTAGE
            const width = this.dimensions.width - borderSize
            const height = this.dimensions.height - borderSize
            const xPos = this.position.x + (borderSize / 2)
            const yPos = this.position.y + (borderSize / 2)
            ctx.fillRect(xPos, yPos, width, height)

            if (this.displayTimeBar) {
                let timeBarPosX = lerp(xPos, xPos + width / 2, this.timeBarElapsed / this.timeBarDuration)
                let timeBarWidth = lerp(width, 0, this.timeBarElapsed / this.timeBarDuration)
                ctx.fillStyle = TILE_LABEL_COLOR
                ctx.fillRect(timeBarPosX, yPos, timeBarWidth, height)
            }

            ctx.scale(scaleFactor, scaleFactor)
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.font = this.font
            ctx.fillStyle = "#000000"
            const playerStatusWidth = this.dimensions.width / this.players.length
            let xOffset = 0
            for (let player of this.players) {
                let dollarSign = player.score < 0 ? "-$" : "$"
                ctx.fillText(
                    player.name + " | " + dollarSign + Math.abs(player.score),
                    (this.position.x + xOffset + (playerStatusWidth / 2)) / scaleFactor,
                    (this.position.y + (this.dimensions.height / 2)) / scaleFactor
                )
                xOffset += playerStatusWidth
            }
            ctx.setTransform(1, 0, 0, 1, 0, 0)
        }
    }


    function* rgbCycle() {

        function intToHex(value) {
            let hexVal = Math.floor(value).toString(16)
            if (hexVal.length === 1) {
                hexVal = "0" + hexVal
            }
            return hexVal
        }

        let i = 0
        while (true) {
            let r = Math.sin(0.07 * i) * 127 + 128
            let g = Math.sin(0.07 * i + 2) * 127 + 128
            let b = Math.sin(0.07 * i + 4) * 127 + 128
            yield "#" + intToHex(r) + intToHex(g) + intToHex(b)
            i = (i + 1) % 4096
        }
    }


    class GameOverScreen extends Entity {
        constructor(players, canvasElement) {
            super(new Position(0, 0), new Dimensions(canvasElement.width, canvasElement.height))
            this.players = players
            this.backgroundColor = "#000000"
            this.rgbCycle = rgbCycle()
        }

        update(elapsedTime, canvasElement) {
            this.dimensions.width = canvasElement.width
            this.dimensions.height = canvasElement.height
            this.backgroundColor = this.rgbCycle.next().value
        }

        draw(ctx, canvasElement, scaleFactor) {
            ctx.fillStyle = this.backgroundColor
            ctx.fillRect(this.position.x, this.position.y, this.dimensions.width, this.dimensions.height)

            ctx.scale(scaleFactor, scaleFactor)
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.font = TILE_FONT_SIZE + "px " + TILE_FONT

            const maxScore = Math.max(...this.players.map(p => p.score))
            const winningPlayers = []
            for (let player of this.players) {
                if (player.score === maxScore) {
                    winningPlayers.push(player)
                }
            }

            const winnerText = (() => {
                if (winningPlayers.length === 1) {
                    return winningPlayers[0].name + " wins!!"
                } else {
                    return "Draw!!"
                }
            })()

            let shadowOffset = TEXT_SHADOW_OFFSET * scaleFactor
            let blackTextXOffset = ((this.dimensions.width / 2) + shadowOffset) / scaleFactor
            let blackWinnerTextYOffset = ((this.dimensions.height / 3) + shadowOffset) / scaleFactor

            let whiteTextXOffset = ((this.dimensions.width / 2)) / scaleFactor
            let whiteWinnerTextYOffset = ((this.dimensions.height / 3)) / scaleFactor

            ctx.fillStyle = "#000000"
            ctx.fillText(winnerText, blackTextXOffset, blackWinnerTextYOffset)
            ctx.fillStyle = "#ffffff"
            ctx.fillText(winnerText, whiteTextXOffset, whiteWinnerTextYOffset)

            this.players.sort((a, b) => b.score - a.score)

            const fontMetrics = ctx.measureText("H")
            const fontHeight = fontMetrics.actualBoundingBoxAscent + fontMetrics.actualBoundingBoxDescent
            const yIncrement = (fontHeight * scaleFactor) + (TILE_FONT_SIZE * 0.75 * scaleFactor)

            let blackPlayerTextYOffset = blackWinnerTextYOffset * 2
            let whitePlayerTextYOffset = whiteWinnerTextYOffset * 2
            for (let player of this.players) {
                let dollarSign = player.score < 0 ? "-$" : "$"
                let playerText = player.name + " | " + dollarSign + Math.abs(player.score)
                ctx.fillStyle = "#000000"
                ctx.fillText(playerText, blackTextXOffset, blackPlayerTextYOffset)
                ctx.fillStyle = "#ffffff"
                ctx.fillText(playerText, whiteTextXOffset, whitePlayerTextYOffset)
                blackPlayerTextYOffset += yIncrement
                whitePlayerTextYOffset += yIncrement
            }

            ctx.setTransform(1, 0, 0, 1, 0, 0)
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
                board = new Board(gameBoardData, canvasElement, 1, 0.90)
                statusBar = new StatusBar(playersState, canvasElement, 1, 0.10)
                gameEntities.push(board)
                gameEntities.push(statusBar)
                main(totalSimTime, game)
            })
        })
    })();


    function categoryToColumn(categoryKey) {
        for (let i = 0; i < board.tiles.length; i++) {
            if (board.tiles[i][0].categoryKey === categoryKey) {
                return i
            }
        }
    }


    function amountToRow(col, amount) {
        for (let j = 0; j < board.tiles[col].length; j++) {
            if (board.tiles[col][j].label === amount) {
                return j
            }
        }
    }


    function gameOver(players) {
        for (let entity of gameEntities) {
            entity.dead = true
        }
        const gameOverScreen = new GameOverScreen(players, canvasElement)
        gameEntities.push(gameOverScreen)
    }


    return {
        setCategoryHighlight: function (categoryKey) {
            let col = categoryToColumn(categoryKey)
            board.setColumnHighlight(col)
        },
        unsetCategoryHighlight: function (categoryKey) {
            let col = categoryToColumn(categoryKey)
            board.unsetColumnHighlight(col)
        },
        flickerTile: function (categoryKey, amount, flickerCount, flickerInterval) {
            let col = categoryToColumn(categoryKey)
            let row = amountToRow(col, amount)
            board.tiles[col][row].flicker(flickerCount, flickerInterval)
        },
        markAnswered: function (categoryKey, amount) {
            let col = categoryToColumn(categoryKey)
            let row = amountToRow(col, amount)
            board.tiles[col][row].markAnswered()
        },
        revealClue: function (categoryKey, amount) {
            let col = categoryToColumn(categoryKey)
            let row = amountToRow(col, amount)
            board.tiles[col][row].reveal()
            statusBar.startTimeBar(TIME_BAR_DURATION, () => onClueExpired(categoryKey, amount))
        },
        pauseTimeBar: function () {
            statusBar.pauseTimeBar()
        },
        resumeTimeBar: function () {
            statusBar.resumeTimeBar()
        },
        resetTimeBar: function () {
            statusBar.resetTimeBar()
        },
        setColumnHighlight: function (col) {
            board.setColumnHighlight(col)
        },
        unsetColumnHighlight: function (col) {
            board.unsetColumnHighlight(col)
        },
        updatePlayersState: function (players) {
            statusBar.players = players
        },
        currentRound: function () {
            return board.currentRound
        },
        gameOver: function (players) {
            gameOver(players)
        },
        kill: function () {
            GAMEBOARD_STOP_GAME_LOOP = true
        },
        toggleDebugFlag: function () {
            DEBUG_FLAG = !DEBUG_FLAG
        }
    }
}
