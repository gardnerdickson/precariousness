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
        console.debug("Received message:", event)
        const message = JSON.parse(event.data)
        if ("error" in message) {
            console.error(message.error)
        } else {
            let operation = message.operation
            if (this.handlers.has(operation)) {
                this.handlers.get(operation)(message.payload)
            } else {
                console.warn("Encountered unregistered route:", event)
            }
        }
    }

    sendMessage(operation, obj) {
        const message = {"operation": operation, "payload": obj}
        console.debug("Sending message:", message)
        this.websocket.send(JSON.stringify(message))
    }
}


const service = {
    newPlayer: function () {
        return fetch("/new_player", {method: "POST"})
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to register player")
                }
                return response.json()
            })
    },
    getGameBoardState: function () {
        return fetch("/get_game_board_state", {method: "POST"})
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to get game board")
                }
                return response.json()
            })
    },
    getPlayersState: function () {
        return fetch("/get_players_state", {method: "POST"})
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to get players state")
                }
                return response.json()
            })
    }
}
