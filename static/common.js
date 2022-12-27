
function hideScreens() {
    d.querySelectorAll(".hideable").forEach(function (el) {
        el.style.display = "none"
    })
}


class SocketMessageRouter {

    constructor() {
        self.handlers = new Map()
    }

    addRoute(route, handler) {
        if (self.handlers.has(route)) {
            throw Error("Route " + route + " already registered")
        }
        self.handlers.set(route, handler)
    }

    onmessage(event) {
        console.debug("Received message:", event)
        const message = JSON.parse(event.data)
        if ("error" in message) {
            console.error(message.error)
        } else {
            let operation = message.operation
            if (self.handlers.has(operation)) {
                self.handlers.get(operation)(message.payload)
            } else {
                console.warn("Encountered unregistered route:", event)
            }
        }
    }
}


const service = {
    newPlayer: function() {
        return fetch("/new_player", {method: "POST"})
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to register player")
                }
                return response.json()
            })
    },
    getGameBoard: function() {
        return fetch("/get_gameboard", {method: "POST"})
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to get game board")
                }
                return response.json()
            })
    },
    markTileUsed: function(round, category, amount) {
        const tile_request_body = {
            "round": round,
            "category": category,
            "amount": amount
        }
        return fetch("/mark_tile_used", {
            method: "POST",
            data: JSON.stringify(tile_request_body)
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to mark tile as used")
                }
                return response.json()
            })
    }
}
