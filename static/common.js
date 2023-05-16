function hideScreens() {
    d.querySelectorAll(".hideable").forEach(function (el) {
        el.style.display = "none"
    })
}


class SocketMessageRouter {

    constructor(ws_url) {
        this.handlers = new Map()
        this.websocket = new WebSocket(ws_url)

        this.websocket.onmessage = (event) => this.onMessage(event)
        this.websocket.onopen = (event) => this.onOpen(event)
    }

    addRoute(route, handler) {
        if (this.handlers.has(route)) {
            throw Error("Route " + route + " already registered")
        }
        this.handlers.set(route, handler)
    }

    onOpen(event) {
        console.debug("Websocket opened:", event)
    }

    onMessage(event) {
        event.data.text().then((rawMessage) => {
            console.debug("Received message:", rawMessage)
            const message = JSON.parse(rawMessage)
            if ("error" in message) {
                console.error(message.error)
            } else {
                let operation = message.operation
                if (this.handlers.has(operation)) {
                    this.handlers.get(operation)(message.payload)
                } else {
                    console.warn("Encountered unregistered route:", message)
                }
            }
        })
    }

    sendMessage(operation, gameId, obj) {
        const message = {"operation": operation, "gameId": gameId, "payload": obj}
        console.debug("Sending message:", message)
        this.websocket.send(JSON.stringify(message))
    }
}


const service = {
    headers: {"Content-Type": "application/json"},

    _logAndThrow: function(response, exceptionMessage) {
        response.json().then((body) => {
            if (body.hasOwnProperty("error")) {
                console.error("Error: ", body.error)
            }
            throw new Error(exceptionMessage)
        })
    },

    newGame: function() {
        return fetch("/init_game", {method: "POST"})
            .then((response) => {
                if (!response.ok) {
                    this._logAndThrow(response, "Failed to initialize new game")
                }
                return response.json()
            })
    },
    newHost: function(gameId) {
        const postBody = {gameId: gameId}
        return fetch("/new_host", {method: "POST", headers: this.headers, body: JSON.stringify(postBody)})
            .then((response) => {
                if (!response.ok) {
                    this._logAndThrow(response, "Failed to register host")
                }
                return response.json()
            })
    },
    newPlayer: function (gameId) {
        const postBody = {gameId: gameId}
        return fetch("/new_player", {method: "POST", headers: this.headers, body: JSON.stringify(postBody)})
            .then((response) => {
                if (!response.ok) {
                    this._logAndThrow(response, "Failed to register player")
                }
                return response.json()
            })
    },
    getGameBoardState: function (gameId) {
        const postBody = {gameId: gameId}
        return fetch("/get_game_board_state", {method: "POST", headers: this.headers, body: JSON.stringify(postBody)})
            .then((response) => {
                if (!response.ok) {
                    this._logAndThrow(response, "Failed to get game board")
                }
                return response.json()
            })
    },
    getPlayersState: function (gameId) {
        const postBody = {gameId: gameId}
        return fetch("/get_players_state", {method: "POST", headers: this.headers, body: JSON.stringify(postBody)})
            .then((response) => {
                if (!response.ok) {
                    this._logAndThrow(response, "Failed to get players state")
                }
                return response.json()
            })
    }
}
