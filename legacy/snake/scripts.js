const AREA_WIDTH = 50
const AREA_HEIGHT = 50
const MIN_SPEED = 40
const ARROW_TOP = 38
const ARROW_BOTTOM = 40
const ARROW_LEFT = 37
const ARROW_RIGHT = 39
const DIRECTIONS = {
    [ARROW_TOP]: [0, -1],
    [ARROW_BOTTOM]: [0, 1],
    [ARROW_LEFT]: [-1, 0],
    [ARROW_RIGHT]: [1, 0]
}

const getRandomPoint = () => {
    return [
        Math.floor(Math.random() * AREA_WIDTH),
        Math.floor(Math.random() * AREA_HEIGHT)
    ]
}

function Snake(config = {}) {
    Object.assign(this, {
        arena,
        direction: DIRECTIONS[ARROW_BOTTOM],
        startLength: 3,
        interval: 200,
        position: getRandomPoint(),
        links: [],
        bobPosition: [-1, -1],
        onEnd: () => null,
        onBob: () => null,
        step: undefined
    }, config)

    const [left, top] = this.position

    for (let i = 0; i < this.startLength; i++) {
        this.addLink([
            left + -1 * this.direction[0] * i,
            top + -1 * this.direction[1] * i
        ])
    }
}

Snake.prototype = {
    setDirection(direction) {
        this.direction = direction
    },
    setBobPosition(bobPosition) {
        this.bobPosition = bobPosition
    },
    remove() {
        Array.from(document.getElementsByClassName('snake-link')).forEach((item) => { item.parentNode.removeChild(item) })
        clearTimeout(this.step)
    },
    addLink([left, top]) {
        const newLink = document.createElement("div")
        newLink.classList.add('snake-link')
        newLink.style.left = `${left}vh`
        newLink.style.top = `${top}vh`
        this.links.push(this.arena.appendChild(newLink))
    },
    eatBob([left, top]) {
        const [bobLeft, bobTop] = this.bobPosition
        if (left === bobLeft && top === bobTop) {
            this.addLink([left, top])
            this.onBob()
        }
    },
    touchSelf([left, top]) {
        return this.links.findIndex(element => {
            return parseInt(element.style.left) === left && parseInt(element.style.top) === top
        }) > -1
    },
    touchBorder([left, top]) {
        if (left < 0 || left >= AREA_WIDTH) {
            return 'Border H'
        }
        if (top < 0 || top >= AREA_HEIGHT) {
            return 'Border V'
        }
    },
    offsetPosition([left, top]) {
        const [offsetLeft, offsetTop] = this.direction
        return [left + offsetLeft, top + offsetTop]
    },
    nextMove() {
        const speed = Math.max(this.interval - (this.links.length - 3) * 10, MIN_SPEED)
        this.step = setTimeout(() => {
            this.position = this.offsetPosition(this.position)
            if (this.touchBorder(this.position)) {
                this.onEnd('Touch Border')
            }
            else if (this.touchSelf(this.position)) {
                this.onEnd('Touch Self')
            } else {
                this.moveSnake()
                this.eatBob(this.position)
                this.nextMove()
                document.getElementById('s_position').innerHTML = `${this.position[0]}vh : ${this.position[1]}vh`
                document.getElementById('s_direction').innerHTML = JSON.stringify(this.direction)
                document.getElementById('s_counter').innerHTML = this.links.length
                document.getElementById('s_interval').innerHTML = speed
            }
        }, speed)
    },
    moveSnake() {
        let [left, top] = this.position
        let c = 0
        let nextLeft = left
        let nextTop = top
        for (let i = 0; i < this.links.length; i++) {
            nextLeft = parseInt(this.links[i].style.left)
            nextTop = parseInt(this.links[i].style.top)

            this.links[i].style.left = `${left}vh`
            this.links[i].style.top = `${top}vh`

            left = nextLeft
            top = nextTop
        }
    }
}

function SnakeGame(config = {}) {
    Object.assign(this, {
        direction: DIRECTIONS[ARROW_BOTTOM],
        counter: 0,
        arena: undefined,
        bobPosition: [-1, -1],
        snake: undefined
    }, config)
}

SnakeGame.prototype = {
    changeDirection(event) {
        console.log('event.keyCode:', event.keyCode)
        if (DIRECTIONS[event.keyCode] && this.snake) {
            event.preventDefault()
            this.snake.setDirection(DIRECTIONS[event.keyCode])
        }
    },
    initEvents() {
        window.addEventListener("keydown", this.changeDirection.bind(this))
    },
    deinitEvents() {
        window.removeEventListener("keydown", this.changeDirection.bind(this))
    },
    initGame() {
        this.snake = new Snake({
            arena: this.arena,
            interval: 200,
            onBob: this.onBob.bind(this),
            onEnd: this.onEnd.bind(this),
        })
        this.addBob()
    },
    resetGame() {
        this.counter = 0
        this.removeBobs()
        this.snake.remove()
        delete this.snake
    },
    message(text) {
        document.getElementById('s_message').innerHTML = text
    },
    addBob() {
        this.bobPosition = getRandomPoint()
        const [left, top] = this.bobPosition
        const newBob = document.createElement('div')
        newBob.classList.add('bob')
        newBob.style.left = `${left}vh`
        newBob.style.top = `${top}vh`
        this.arena.appendChild(newBob)
        this.snake.setBobPosition(this.bobPosition)

    },
    removeBobs() {
        Array.from(this.arena.getElementsByClassName('bob')).forEach((item) => {
            item.parentNode.removeChild(item)
        })
        this.bobPosition = [-1, -1]
    },
    onBob() {
        this.removeBobs()
        this.addBob()
    },
    onEnd(message) {
        this.end(message)
    },
    start() {
        if (this.gameActive) {
            this.end()
        }
        this.arena = document.getElementById('arena')
        this.initEvents()
        this.initGame()
        this.message('Game started')

        this.gameActive = true
        this.snake.nextMove()
    },
    end(message = '') {
        this.deinitEvents()
        this.resetGame()
        this.message(`Game Finished. ${message}`)
        this.gameActive = false
    }
}
