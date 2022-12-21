
function hideAllGameComponents() {
    d.querySelectorAll(".hideable-game-component").forEach(function (el) {
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
        let operation = message.operation
        if (self.handlers.has(operation)) {
            self.handlers.get(operation)(message.payload)
        } else {
            console.warn("Encountered unregistered route:", event)
        }
    }
}
