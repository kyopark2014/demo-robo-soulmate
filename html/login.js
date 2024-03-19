function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}


// Chat UI
const myForm = document.querySelector('#my-form');
const userInput = document.querySelector('#userId');
const convtypeInput = document.querySelector('#convtype');

// Common
let userId = localStorage.getItem('userId'); // set userID if exists 
if(userId=="") {
    userId = uuidv4();
}
else {
    userInput.value = userId
}
console.log('userId: ', userId);

myForm.addEventListener('submit', onSubmit);

let conversationType = localStorage.getItem('convType'); // set conversationType if exists 
if(conversationType != '') {
    convtypeInput.value = conversationType;
}
else {
    convtypeInput.value = "normal"  // general conversation
}

console.log(userInput.value);
console.log(convtypeInput.value);

// provisioning
getProvisioningInfo(userId);
getVoiceProvisioningInfo(userId);

function onSubmit(e) {
    e.preventDefault();
    console.log(userInput.value);
    console.log(convtypeInput.value);

    localStorage.setItem('userId',userInput.value);
    console.log('Save Profile> userId:', userInput.value)    

    localStorage.setItem('convType',convtypeInput.value);
    console.log('Save Profile> convtype:', convtypeInput.value)

    window.location.href = "chat.html";
}

function getProvisioningInfo(userId) {
    const uri = "provisioning";
    const xhr = new XMLHttpRequest();

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            let provisioning_info = JSON.parse(response['info']);
            console.log("provisioning info: " + JSON.stringify(provisioning_info));
                        
            let wss_url = provisioning_info.wss_url;
            console.log("wss_url: ", wss_url);

            localStorage.setItem('wss_url',wss_url);
        }
    };

    var requestObj = {
        "userId": userId
    }
    console.log("request: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);   
}

function getVoiceProvisioningInfo(userId) {
    const uri = "voice_provisioning";
    const xhr = new XMLHttpRequest();

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            let voice_provisioning_info = JSON.parse(response['info']);
            console.log("voice provisioning info: " + JSON.stringify(voice_provisioning_info));
                        
            let voice_wss_url = voice_provisioning_info.wss_url;
            console.log("voice_wss_url: ", voice_wss_url);

            localStorage.setItem('voice_wss_url',voice_wss_url);
        }
    };

    var requestObj = {
        "userId": userId
    }
    console.log("request: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);   
}



// Camaera UI

// Camera
const startButton = document.querySelector(".start-button");
const previewButton = document.querySelector(".preview-button");
const emotionButton = document.querySelector(".emotion-button");
const playButton = document.querySelector(".play-button");

//event
startButton.addEventListener("click", videoStart);
emotionButton.addEventListener("click", emotion);
playButton.addEventListener("click", playSpeech);

let audio_file = "";

let previewlist = [];
let fileList = [];
const maxImgItems = 1;
let drawingIndex = 0;
let emotionValue;
let generation;
let gender;

const previewPlayer = document.querySelector("#preview");
let canvas = document.getElementById('canvas');
canvas.width = previewPlayer.width;
canvas.height = previewPlayer.height;

function videoStart() {    
    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => {
            previewPlayer.srcObject = stream;

            console.log('video started!')
        })
}

function preview() {
    canvas.getContext('2d').drawImage(previewPlayer, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(function (blob) {
        const img = new Image();
        img.src = URL.createObjectURL(blob);

        console.log(blob);

        // downloadButton.href=img.src;
        // console.log(downloadButton.href);
        // downloadButton.download =`capture_${new Date()}.jpeg`; 
    }, 'image/png');
}

function emotion() {
    canvas.getContext('2d').drawImage(previewPlayer, 0, 0, canvas.width, canvas.height);
    drawingIndex = 0;

    console.log('event for emotion');

    //getEmotion();
    makeGreetingMessage();
}

function makeGreetingMessage() {
    const uri = "greeting";
    const xhr = new XMLHttpRequest();

    xhr.open("POST", uri, true);

    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            let msg = xhr.responseText;            
            console.log("msg: " + msg);

            requestId = uuidv4();
            addReceivedMessage(requestId, msg);   
        }
        else {
            console.log("response: " + xhr.responseText);
        }
    };
    
    // console.log('uuid: ', uuid);

    canvas.toBlob(function (blob) {
        // var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});
        xhr.send(blob);
    }, {type: 'image/png'});
}



function getEmotion() {
    // const uri = cloudfrntUrl + "emotion";
    const uri = "greeting";
    const xhr = new XMLHttpRequest();

    xhr.open("POST", uri, true);

    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            console.log("response: " + JSON.stringify(response));

            userId = response.id;
            console.log("userId: " + userId);

            gender = response.gender;
            console.log("gender: " + gender);

            generation = response.generation;
            console.log("generation: " + generation);

            let ageRangeLow = JSON.parse(response.ageRange.Low);
            let ageRangeHigh = JSON.parse(response.ageRange.High);
            let ageRange = `Age: ${ageRangeLow} ~ ${ageRangeHigh}`; // age   
            console.log('ages: ' + ageRange);

            let smile = response.smile;
            console.log("smile: " + smile);

            let eyeglasses = response.eyeglasses;
            console.log("eyeglasses: " + eyeglasses);

            let sunglasses = response.sunglasses;
            console.log("sunglasses: " + sunglasses);

            let beard = response.beard;
            console.log("beard: " + beard);

            let mustache = response.mustache;
            console.log("mustache: " + mustache);

            let eyesOpen = response.eyesOpen;
            console.log("eyesOpen: " + eyesOpen);

            let mouthOpen = response.mouthOpen;
            console.log("mouthOpen: " + mouthOpen);

            emotionValue = response.emotions.toLowerCase();
            console.log("emotion: " + emotionValue);

            let emotionText = "Emotion: ";
            if (emotionValue == "happy") emotionText += "행복";
            else if (emotionValue == "surprised") emotionText += "놀람";
            else if (emotionValue == "calm") emotionText += "평온";
            else if (emotionValue == "angry") emotionText += "화남";
            else if (emotionValue == "fear") emotionText += "공포";
            else if (emotionValue == "confused") emotionText += "혼란스러움";
            else if (emotionValue == "disgusted") emotionText += "역겨움";
            else if (emotionValue == "sad") emotionText += "슬픔";

            let features = "Features:";
            if (smile) features += ' 웃음';
            if (eyeglasses) features += ' 안경';
            if (sunglasses) features += ' 썬글라스'; 
            if (beard) features += ' 수염';
            if (mustache) features += ' 콧수염';
            if (eyesOpen) features += ' 눈뜨고있음';
            if (mouthOpen) features += ' 입열고있음';
            console.log("features: " + features);

            let genderText;
            if (gender == 'male') genderText = '남자'
            else genderText = '여자'
            let profileText = ageRange + ' (' + genderText + ')';
            console.log("profileText: " + profileText);

            canvas.toBlob(function (blob) {
                const img = new Image();
                img.src = URL.createObjectURL(blob);

                console.log(blob);

                //    downloadButton.href = img.src;
                //    console.log(downloadButton.href);
                //    downloadButton.download = `capture_${emotionValue}_${gender}_${middleAge}_${new Date()}.jpeg`;
            }, 'image/png');

            console.log("emotion: ", emotionValue);

            getMessage();
        }
        else {
            // profileInfo_features.innerHTML = ""
        }
    };

    // console.log('uuid: ', uuid);

    canvas.toBlob(function (blob) {
        xhr.send(blob);
    });
}

function getDate(current) {    
    return current.toISOString().slice(0,10);
}

function getTime(current) {
    let time_map = [current.getHours(), current.getMinutes(), current.getSeconds()].map((a)=>(a < 10 ? '0' + a : a));
    return time_map.join(':');
}


function playSpeech() {
    console.log('event for play');

    let audio = new Audio(audio_file);
    audio.play();
}

