let grid = 1;
let num = 3;
let colors = ["#0ea9eb", "#fb6819", "#e70e75"];
let baseColor = 84;
let bg = "#1F1F1F";
let pg;
//randoms
let randomTile = Array(num).fill(0.5), randomEllipse = 0.5, randomRotateTriangle = 0.5, randomRotateSingleSideTriangle = 0.5, randomRotateSingleTriangle = 0.5, randomRotateEllipse = 0.5, randomShuffleArray = 0.5;
let font;
let webcam;
let webcamHeight = 285;
let webcamWidth = 295;
let canvasHeight= 400;
const socket = new WebSocket('wss://image2logo-b2a51e3b7966.herokuapp.com:443');


function preload(){
    webcam = loadImage("../Backend/smile_detected.jpg");
    font = loadFont("fonts/Montserrat-Regular.ttf");
}
function setup() {
    textFont(font)
    socket.addEventListener('open', () => {
        console.log('Connected to the WebSocket server');
    })
    socket.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        if (data.detected){
            updatePG(data.image)
        }
        webcam = loadImage("../Backend/smile_detected.jpg");
    })
    createCanvas(window.innerWidth, window.innerHeight);

    textAlign(CENTER);
    textStyle(NORMAL);

    // webcam = createCapture(VIDEO)
    // webcam.loop()
    // webcam.hide()

    noStroke();
    strokeCap(SQUARE);
    colors = shuffle(colors);
    setupPG();
    noSmooth();
    textAlign(LEFT, CENTER);

    background(bg);
    pg.background(bg);
    createGrid();
    drawGrayGrid();
    updatePGPixels();
    drawColorGrid();
}

function setupPG() {
    pg = createGraphics(canvasHeight*0.4, canvasHeight*0.4); // Nao modificar esses valores!!!
    pg.noStroke();
    pg.noSmooth();
    pg.blendMode(ADD);
}

function draw() {
    push();
    translate(width,0);
    scale(-1,1)
    imageMode(CENTER);
    image(webcam, window.innerWidth/2,webcamHeight/2 + window.innerHeight*0.02, webcamWidth, webcamHeight);
    pop();

    renderText("Sorria para ver sua foto ->", window.innerWidth/10, window.innerHeight*0.2);
    renderText("IMAGE2LOGO", window.innerWidth*0.42, window.innerHeight*0.9);
    renderText("© Todos os direitos reservados - Laboratorio ICON\n" + "Codigo original por Francisco Barretto", window.innerWidth*0.02, window.innerHeight*0.9, window.innerWidth*0.010);
}

function createGrid() {
    pg.background(bg);
    background(bg);

    for (let i = 0; i < num; i++) {
        drawGrid(pg, i);
    }
}

function drawGrayGrid() {
    push();
    translate(pg.width + (window.innerWidth / 2) - (canvasHeight * 0.8) - (window.innerWidth * 0.025), pg.height + (window.innerHeight / 2) - (window.innerHeight * 0.15));
    rotate(-PI);
    image(pg,0,0);
    rotate(-PI/2);
    image(pg,0,0);
    rotate(-PI/2);
    image(pg,0,0);
    rotate(-PI/2);
    image(pg,0,0);
    pop();
}

function drawColorGrid() {
    push();
    translate(pg.width + (window.innerWidth / 2) + (window.innerWidth * 0.025), pg.height + (window.innerHeight / 2) - (window.innerHeight * 0.15));
    rotate(-PI);
    image(pg,0,0);
    rotate(-PI/2);
    image(pg,0,0);
    rotate(-PI/2);
    image(pg,0,0);
    rotate(-PI/2);
    image(pg,0,0);
    pop();
}


function drawGrid(pg, pos) {
    print("update PG");

    for (let i = 0; i < grid; i++) {
        for (let j = 0; j < grid; j++) {
            tile(j * pg.width/grid, i * pg.height/grid, pg.width/grid, pos);
        }
    }
}

function tile(x, y, size, pos) {
    console.log(pos, randomTile[pos]);

    let rand = randomTile[pos];
    let color = baseColor*(pos);
    console.log(color);
    if (rand>0.5)
        drawEllipseTile(x,y,size, pos, color);
    else {
        if (rand>0.3){
            drawSingleTriangle(x,y,size, pos, color);
        } else if (rand>0.2){
            drawTriangle(x,y,size, pos, color);
        } else {
            drawSideTriangle(x,y,size, pos, color);
        }
    }
}

function updatePG(data) {
    let seed = cyrb53(data);

    randomTile[0] = Number(String(seed).substring(0, 2))/100.0;
    randomTile[1] = Number(String(seed).substring(2, 4))/100.0;
    randomTile[2] = Number(String(seed).substring(4, 6))/100.0;
    randomEllipse = Number(String(seed).substring(6, 8))/100.0;
    randomRotateTriangle = Number(String(seed).substring(8, 10))/100.0;
    randomRotateSingleSideTriangle = Number(String(seed).substring(10, 12))/100.0;
    randomRotateSingleTriangle = Number(String(seed).substring(12, 14))/100.0;
    randomRotateEllipse = Number(String(seed).substring(14, 16))/100.0;
    randomShuffleArray = Number(String(seed).substring(16, 18))/100.0;
    console.log(randomTile);
    console.log(randomEllipse, randomRotateTriangle, randomRotateSingleSideTriangle, randomRotateSingleTriangle, randomRotateEllipse, randomShuffleArray);

    setupPG();

    createGrid();
    drawGrayGrid();
    updatePGPixels();
    drawColorGrid();
}

function updatePGPixels() {
    for (let i = 0; i< pg.width; i++) {
        for (let j = 0; j< pg.height; j++) {
            let c = pg.get(i,j);

            if (c[0]>=252)
                pg.set(i,j,color(colors[0]));
            else if (c[0]>=162)
                pg.set(i,j,color(colors[1]));
            else if (c[0]>=84)
                pg.set(i,j,color(colors[2]));
        }
    }
    pg.updatePixels();
}

function drawTriangle(x,y,size, pos, color) {
    pg.push();
    pg.translate(x+size/2, y+size/2);
    pg.rotate(floor(randomRotateTriangle*4) * PI/2);
    pg.translate(-size/2, -size/2);

    pg.fill(color);

    pg.triangle(0,0,0,size/2,size/2,0);

    pg.pop();
}

function drawSideTriangle(x,y,size, pos, color) {
    pg.push();
    pg.translate(x+size/2, y+size/2);
    pg.rotate(floor(randomRotateSingleSideTriangle*4) * PI/2);
    pg.translate(-size/2, -size/2);

    pg.fill(color);

    pg.triangle(0,0,0,size,size/2,size/2);

    pg.pop();
}

function drawSingleTriangle(x,y,size, pos=0, color) {
    pg.push();
    pg.translate(x+size/2, y+size/2);
    pg.rotate(floor(randomRotateSingleTriangle*4) * PI/2);
    pg.translate(-size/2, -size/2);

    pg.fill(color);

    pg.triangle(0,0,0,size,size,0);

    pg.pop();
}

function drawEllipseTile(x,y,size, pos, color) {

    pg.fill(color);

    if (randomEllipse>0.5) {
        pg.push();
        pg.translate(x+size/2, y+size/2);
        pg.rotate(floor(randomRotateEllipse*4) * PI/2);
        pg.translate(-size/2, -size/2);
        pg.arc(0,size/2,size, size, PI+HALF_PI, HALF_PI);
        pg.pop();
    } else {
        pg.ellipse(x+size/2,y+size/2,size*.9,size*.9);
    }

}

function renderText(info, x, y, size = 30) {
    textFont()
    push();
    smooth();
    fill(255);
    textSize(size);
    text(info, x, y);
    pop();
}

const shuffle = (array) => {
    return array.sort(() => randomShuffleArray - 0.5);
};

const cyrb53 = (str, seed = 0) => {
    let h1 = 0xdeadbeef ^ seed, h2 = 0x41c6ce57 ^ seed;
    for(let i = 0, ch; i < str.length; i++) {
        ch = str.charCodeAt(i);
        h1 = Math.imul(h1 ^ ch, 2654435761);
        h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    h1  = Math.imul(h1 ^ (h1 >>> 16), 2246822507);
    h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2  = Math.imul(h2 ^ (h2 >>> 16), 2246822507);
    h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);

    return 4294967296 * (2097151 & h2) + (h1 >>> 0);
};

