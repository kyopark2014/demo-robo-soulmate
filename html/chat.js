const protocol = 'WEBSOCKET'; // WEBSOCKET 
const langstate = 'korean'; // korean or english
const enableTTS = true;
const enableDelayedMessage = false; // in order to manipulate the voice messages
const speechType = 'both';  // local or robot or both

if(enableTTS && (speechType=='local' || speechType=='both')) {
    var AudioContext;
    var audioContext;

    window.onload = function() {
        navigator.mediaDevices.getUserMedia({ audio: true }).then(() => {
            AudioContext = window.AudioContext || window.webkitAudioContext;
            audioContext = new AudioContext();
        }).catch(e => {
            console.error(`Audio permissions denied: ${e}`);
        });
    }
}

// Common
let userId = localStorage.getItem('userId'); // set userID if exists 
if(userId=="" || userId==null) {
    userId = uuidv4();
}
console.log('userId: ', userId);

let userName = localStorage.getItem('userName'); // set userID if exists 
if(userName=="" || userName==null) {
    userName = 'Maltese';
}
console.log('userName: ', userName);

let silientMode = true; // true: no voice of robot
let robotSpeech = localStorage.getItem('robotSpeech'); // set userID if exists 
if(robotSpeech=="" || robotSpeech==null) {
    robotSpeech = 'Silent';    
}
console.log('robotSpeech: ', robotSpeech);

if(robotSpeech=='Silent') {
    silientMode = true;
}
else {
    silientMode = false;
}
console.log('silientMode: ', silientMode);

// chat session
let endpoint = localStorage.getItem('wss_url');  
if(endpoint=="") {
    console.log('provisioning is required!');
}
console.log('endpoint: ', endpoint);

let webSocket
let isConnected;
if(protocol == 'WEBSOCKET') {
    webSocket = connect(endpoint, 'initial');
} 

// voice session
let voiceEndpoint = localStorage.getItem('voice_wss_url');
if(voiceEndpoint=="") {
    console.log('voice provisioning is required!');
}
console.log('voiceEndpoint: ', voiceEndpoint);

let voiceWebSocket
let isVoiceConnected;
if(protocol == 'WEBSOCKET') {
    voiceWebSocket = voiceConnect(voiceEndpoint, 'initial');
}

console.log('feedback...');
const feedback = document.getElementById('feedback');
feedback.style.display = 'none'; 

// Hashmap
HashMap = function() {
    this.map = new Array();
};

HashMap.prototype = {
    put: function(key, value) {
        this.map[key] = value;
    },
    get: function(key) {
        return this.map[key];
    },
    size: function() {
        var keys = new Array();
        for(i in this.map) {
            keys.push(i);
        }
        return keys.length;
    },
    remove: function(key) {
        delete this.map[key];
    },
    getKeys: function() {
        var keys = new Array();
        for(i in this.map) {
            keys.push(i);
        }
        return keys;
    }
};

// messag method 
let undelivered = new HashMap();
let retry_count = 0;
function sendMessage(message) {
    if(!isConnected) {
        console.log('reconnect...'); 
        webSocket = connect(endpoint, 'reconnect');
        
        if(langstate=='korean') {
            addNotifyMessage("재연결중입니다. 연결후 자동 재전송합니다.");
        }
        else {
            addNotifyMessage("We are connecting again. Your message will be retried after connection.");                        
        }

        undelivered.put(message.request_id, message);
        console.log('undelivered message: ', message);
        
        return false
    }
    else {
        webSocket.send(JSON.stringify(message));     
        console.log('sendMessage: ', message);   

        return true;
    }     
}

// keep alive
let tm;
let chromeTimer = 300;
function ping() {
    console.log('->ping');
    webSocket.send('__ping__');

    chromeTimer = chromeTimer - 50;
    if(chromeTimer<60) {
        chromeTimer = 300;
        window.location.href = "chat.html";
    }

    tm = setTimeout(function () {
        console.log('reconnect...');    
        
        isConnected = false
        webSocket = connect(endpoint, 'reconnect');

    }, 5000);
}
function pong() {
    clearTimeout(tm);
}

let voiceTm;
function voicePing() {
    console.log('->voice ping');
    voiceWebSocket.send('__ping__');
    voiceTm = setTimeout(function () {
        console.log('voice reconnect...');    
        
        isVoiceConnected = false
        voiceWebSocket = voiceConnect(voiceEndpoint, 'reconnect');
        
    }, 5000);
}
function voicePong() {
    clearTimeout(voiceTm);
}

let retryCounter;
function checkingDelayedPlayList() {
    // console.log('->checking delayed played list ('+retryCounter+')');  
    playAudioList();

    let isCompleted = true;
    for(let i=0; i<playList.length;i++) {
        if(playList[i].played == false) {
            isCompleted = false;
            break;
        }
    }
    
    if(isCompleted==true) {
        playList = [];
    } 
    else {
        playTm = setTimeout(function () {           
            retryCounter--;
    
            if(retryCounter>0) {
                checkingDelayedPlayList();
            }
        }, 1000);
    }    
}

// chat session 
let sentance = new HashMap();
let lineText = "";
let playList = [];
let playId = 0;
let requestId = ""
let next = true;
let isPlayedTTS = new HashMap();

// Robot commend
let reservedCommend = new HashMap();
let limitedCommendId = new HashMap(); // once per a game

function initializeCommend() {

    cBark = ['짖어', '짖어봐', '짖어줘', '짖어라', '말해봐', '말해', '소리내봐', '울어봐', '하울링해봐', '하울링해줘', '멍멍해봐', '멍멍해줘', '왈왈해봐', '왈왈해줘', '컹컹해봐', '컹컹해줘']
    for (let i = 0; i < cBark.length; i++) {
      reservedCommend.put(cBark[i], JSON.stringify({"show": "SAD", "move": "seq", "seq":["LOOK_UP"], "say": "멍! 멍! "}));
    }

    cDown = ['앉아', '앉아봐', '앉아줘', '안자', '안자봐', '안자줘', '업드려', '업드려봐', '업드려줘', '앉아있어', '앉아있어봐', '앉아있어줘', '안자있어', '안자있어봐', '안자있어줘','누워있어', '누워있어봐', '누워있어줘', '엎드려있어', '엎드려있어봐', '엎드려있어줘', '앉아있기', '안자있기', '누워있기', '엎드려있기',]
    for (let i = 0; i < cDown.length; i++) {
      reservedCommend.put(cDown[i], JSON.stringify({"show": "HAPPY", "move": "seq", "seq":["SIT", "SIT", "SIT", "SIT", "SIT"], "say": "앉았어."}));
    }

    cCome = ['이리와', '이리와봐', '이리와줘', '여기로와', '이쪽으로와', '내곁으로와', '이리로오렴', '이쪽으로오렴', '가까이다가와', '내곁으로오렴', '이리로와줘', '이리로접근해', '여기로접근해', '이쪽으로접근해', '내곁으로접근해', '이리로다가와', '여기로다가와', '이쪽으로다가와', '내곁으로다가와', '이리로모여', '여기로모여', '이쪽으로모여', '내곁으로모여']
    for (let i = 0; i < cCome.length; i++) {
      reservedCommend.put(cCome[i], JSON.stringify({"show": "HAPPY", "move": "seq", "seq":["MOVE_FORWARD", "MOVE_FORWARD", "MOVE_FORWARD", "MOVE_FORWARD", "MOVE_FORWARD"], "say": "그쪽으로 갈게!"}));
      limitedCommendId.put(cCome[i], 1)
    }

    cGoOut = ['저리가', '저리가봐', '저리가줘', '저리로가', '멀리가', '떨어져', '저쪽으로가', '저곳으로가', '저리로떨어져', '저쪽으로떨어져', '저곳으로떨어져', '저리로물러나', '저쪽으로물러나', '저곳으로물러나', '저리로이동해', '저쪽으로이동해', '저곳으로이동해', '저리로걸어가', '저쪽으로걸어가', '저곳으로걸어가']
    for (let i = 0; i < cGoOut.length; i++) {
      reservedCommend.put(cGoOut[i], JSON.stringify({"show": "HAPPY", "move": "seq", "seq":["MOVE_BACKWARD", "MOVE_BACKWARD", "MOVE_BACKWARD", "MOVE_BACKWARD", "MOVE_BACKWARD"], "say": "멀리 떨어질게!"}));
      limitedCommendId.put(cGoOut[i], 2)
    }

    cNo = ['안돼 그러지마', '안돼', '그러지마', '하지마', '스탑', '멈춰', '그만해', '제발그만해', '이제그만해', '더이상하지마', '금지야', '하면안돼', '절대로하지마', '삼가해', '자제해', '참아', '참아줘', '인내해', '인내하렴', '견뎌내', '참을성있어']
    for (let i = 0; i < cNo.length; i++) {
      reservedCommend.put(cNo[i], JSON.stringify({"show": "SAD", "move": "seq", "seq":["LOOK_LEFT","LOOK_RIGHT", "LOOK_LEFT", "LOOK_RIGHT" ], "say": "알았어 안할게!"}));
    }

    cTurn = ['돌아봐', '돌아', '한바퀴돌아']
    for (let i = 0; i < cTurn.length; i++) {
      reservedCommend.put(cTurn[i], JSON.stringify({"show": "SAD", "move": "seq", "seq":["TURN_LEFT", "TURN_LEFT","TURN_LEFT","TURN_LEFT","TURN_LEFT", "TURN_RIGHT", "TURN_RIGHT","TURN_RIGHT","TURN_RIGHT","TURN_RIGHT"], "say": "알겠어 잘 봐봐!"}));
    }

    cMove = ['움직여', '움직여봐', '갸우뚱해봐', '움직일 수 있어', '고개 흔들어봐', '갸우뚱']
    for (let i = 0; i < cMove.length; i++) {
      reservedCommend.put(cMove[i], JSON.stringify({"show": "SAD", "move": "seq", "seq":[ "ROLL_LEFT","ROLL_LEFT","ROLL_RIGHT","ROLL_RIGHT"], "say": "이렇게요?"}));
    }
}


initializeCommend();

let counter = new HashMap();
function initCommendCounter() {
    counter.put(1, 0);
    counter.put(2, 0);
    counter.put(3, 0);
    counter.put(4, 0);
    counter.put(5, 0);
}

function removeSpecialChars(str) {
    return str.replace(/[^a-zA-Z0-9ㄱ-ㅎㅏ-ㅣ가-힣 ]/g, '').trim();
}

function calculateSimilarity(str1, str2) {
    str1 = removeSpecialChars(str1)
    str2 = removeSpecialChars(str2)
    const longer = str1.length >= str2.length ? str1 : str2;
    const shorter = str1.length < str2.length ? str1 : str2;

    let sameChars = 0;
    for (let i = 0; i < shorter.length; i++) {
        if (str1[i] === str2[i]) {
            sameChars++;
        }
    }

    const similarity = (sameChars / longer.length) * 100;
    return similarity.toFixed(2);
}

function getCommand(commands, message) {
    selectedKey = ""
    selectedScore = -1
    for (const key of commands.getKeys()) {
        score = calculateSimilarity(key, message)
        if (calculateSimilarity(key, message) > 50) {
            if (score > selectedScore ) {
                score = selectedScore
                selectedKey = key
            }
        }
    }
    return commands.get(selectedKey)
}

function isReservedCommend(message){
    // console.log('reservedCommend.get('+message+'): '+ reservedCommend.get(message));

    if(getCommand(reservedCommend, message) == undefined) {
        return false;
    }
    else {
        console.log('reservedCommend.get('+message+'): '+ getCommand(reservedCommend, message));

        return true;
    }    
}



function actionforReservedCommend(requestId, message) {
    let commendId = getCommand(limitedCommendId, message)
    console.log('commendId: ', commendId);
    
    let speech = "";
    if(commendId == undefined) {  // reserved commend but not a limited commend
        console.log('message: ', message);
        
        let command = getCommand(reservedCommend, message)
        console.log('command: ', command);

        if (silientMode==true) {
            let silent_command = {
                "show": JSON.parse(command)["show"],
                "move": JSON.parse(command)["move"],
                "seq": JSON.parse(command)["seq"]
            }
            console.log('show: ', command)["show"];
            console.log('move: ', command)["move"];
            console.log('seq: ', command)["seq"];
            console.log('silent_command: ', silent_command);
            sendControl(userId, "commend", "", silent_command, 0, requestId)
        }
        else {
            sendControl(userId, "commend", "", command, 0, requestId)
        }

        addReceivedMessage(requestId, JSON.parse(command)["say"])

        speech = JSON.parse(command)["say"];  
    }
    else {  // limited commend
        let cnt = counter.get(commendId);
        // console.log('commend counter: ', cnt);

        speech = "";
        if(cnt == undefined || cnt == 0) {
            console.log('message: ', message);
            let command = getCommand(reservedCommend, message);
            console.log('command: ', command);

            if (silientMode==true) {
                let silent_command = {
                    "show": JSON.parse(command)["show"],
                    "move": JSON.parse(command)["move"],
                    "seq": JSON.parse(command)["seq"]
                }
                console.log('silent_command: ', silent_command);
                sendControl(userId, "commend", "", silent_command, 0, requestId)
            }
            else {
                sendControl(userId, "commend", "", command, 0, requestId)
            }
            addReceivedMessage(requestId, JSON.parse(command)["say"])

            counter.put(commendId, 1);
            speech = JSON.parse(command)["say"];  
        }
        else if (cnt>=1) {
            console.log(message+' is only allowed for a time.');

            message = '안돼. 그러지마.';
            console.log('message: ', message);

            if (silientMode==true) {
                let command = getCommand(reservedCommend, message);
                console.log('command: ', command);
                let silent_command = {
                    "show": JSON.parse(command)["show"],
                    "move": JSON.parse(command)["move"],
                    "seq": JSON.parse(command)["seq"]
                }
                console.log('silent_command: ', silent_command);
                sendControl(userId, "commend", "", silent_command, 0, requestId)
            }
            else {
                let command = getCommand(reservedCommend, message);
                console.log('command: ', command);
                sendControl(userId, "commend", "", command, 0, requestId)
            }

            addReceivedMessage(requestId, message)

            speech = message;  
        }
        else {
            console.log('not deifned: '+message+' (cnt='+cnt);
        }
    }

    // speek
    if(enableTTS && speech) {
        console.log('speech: ', speech);
        
        if (silientMode==false) {
            sendControl(userId, 'text', speech, "", 0, requestId);
        }

        console.log('Is already played? ', isPlayedTTS[requestId]);            
        if(isPlayedTTS[requestId] == undefined) {
            playList.push({
                'played': false,
                'requestId': requestId,
                'text': speech
            });
        
            loadAudio(requestId, speech);
                
            next = true;
            playAudioList();                
        }    
        
        retryCounter = 10;
        checkingDelayedPlayList();
        // playList = [];
    } 
}

function connect(endpoint, type) {
    const ws = new WebSocket(endpoint);

    // connection event
    ws.onopen = function () {
        console.log('connected...');
        isConnected = true;

        if(undelivered.size() && retry_count>0) {
            let keys = undelivered.getKeys();
            console.log('retry undelived messags!');            
            console.log('keys: ', keys);
            console.log('retry_count: ', retry_count);

            for(i in keys) {
                let message = undelivered.get(keys[i])
                console.log('message', message)
                if(!sendMessage(message)) break;
                else {
                    undelivered.remove(message.request_id)
                }
            }
            retry_count--;
        }
        else {
            retry_count = 3
        }

        if(type == 'initial')
            setInterval(ping, 40000);  // ping interval: 40 seconds
    };

    // message 
    ws.onmessage = function (event) {     
        isConnected = true;   
        if (event.data.substr(1,8) == "__pong__") {
            console.log('<-pong');
            pong();
            return;
        }
        else {
            response = JSON.parse(event.data)

            if(response.status == 'completed') {     
                console.log('transaction status: completed');
                // console.log('next: ', next); 
                feedback.style.display = 'none';       
                   
                addReceivedMessage(response.request_id, response.msg);  
                // console.log('response.msg: ', response.msg);

                // send received message to score board
                sendMessageToScoreBoard(userId, 'chat', response.msg, response.request_id) 

                if(enableTTS) {                    
                    // console.log('speechType: ', speechType);
                    if(speechType=='robot') {
                        sendControl(userId, 'text', response.msg, "", 0, response.request_id);
                    }
                    else if(speechType=='local') { // local
                        console.log('Is already played? ', isPlayedTTS[response.request_id]);
                        if(isPlayedTTS[response.request_id] == undefined) {
                            requestId = response.request_id;
                            playList.push({
                                'played': false,
                                'requestId': requestId,
                                'text': response.msg
                            });
                            lineText = "";      
                    
                            loadAudio(response.request_id, response.msg);
                            
                            next = true;
                            playAudioList();
                        }    
                    }
                    else if(speechType=='both') {
                        if (silientMode==false) {
                            sendControl(userId, 'text', response.msg, "", 0, response.request_id);
                        }

                        // console.log('Is already played? ', isPlayedTTS[response.request_id]);
                        if(isPlayedTTS[response.request_id] == undefined) {
                            requestId = response.request_id;
                            playList.push({
                                'played': false,
                                'requestId': requestId,
                                'text': response.msg
                            });
                            lineText = "";      
                    
                            loadAudio(response.request_id, response.msg);
                            
                            next = true;
                            playAudioList();
                        }    
                    }
                    
                    retryCounter = 10;
                    checkingDelayedPlayList();
                    // playList = [];
                }      
                
                if(index>maxMsgItems-maxLengthOfHistoryReadable) {
                    updateChatHistory();                    
                } 
            }          
            else if(response.status == 'istyping') {                
                feedback.style.display = 'inline';
                // feedback.innerHTML = '<i>typing a message...</i>'; 
                sentance.put(response.request_id, "");
            }
            else if(response.status == 'proceeding') {
                console.log('transaction status: proceeding...');
                feedback.style.display = 'none';
                sentance.put(response.request_id, sentance.get(response.request_id)+response.msg);              
                
                addReceivedMessage(response.request_id, sentance.get(response.request_id));
                // console.log('response.msg: ', response.msg);
                /// console.log('sentance: ', sentance.get(response.request_id));

                if(enableTTS && (speechType=='local' || speechType=='both')) {
                    lineText += response.msg;
                    lineText = lineText.replace('\n','');
                    if(lineText.length>3 && (response.msg == '.' || response.msg == '?' || response.msg == '!'|| response.msg == ':')) {     
                        console.log('lineText: ', lineText);
                        text = lineText
                        playList.push({
                            'played': false,
                            'requestId': requestId,
                            'text': text
                        });
                        lineText = "";
            
                        isPlayedTTS[response.request_id] = true;
                        loadAudio(response.request_id, text);
                    }
                    
                    requestId = response.request_id;
                    playAudioList();
                } 
            }                
            else if(response.status == 'debug') {
                feedback.style.display = 'none';
                console.log('debug: ', response.msg);
                // addNotifyMessage(response.msg);
                addReceivedMessage(response.request_id, response.msg);  
            }          
            else if(response.status == 'error') {
                feedback.style.display = 'none';
                console.log('error: ', response.msg);

                if(response.msg.indexOf('throttlingException') || response.msg.indexOf('Too many requests') || response.msg.indexOf('too many requests')) {
                    addNotifyMessage('허용된 요청수를 초과하였습니다. 추후 다시 재시도 해주세요.');  
                }
                else {
                    addNotifyMessage(response.msg);
                }                
            }   
        }        
    };

    // disconnect
    ws.onclose = function () {
        console.log('disconnected...!');
        isConnected = false;

        ws.close();
        console.log('the session will be closed');
    };

    // error
    ws.onerror = function (error) {
        console.log(error);
        isConnected = false;

        ws.close();
        console.log('the session will be closed');
    };

    return ws;
}

let redirectTm; // timer for redirection
let remainingRedirectedMessage;  // merge two consecutive messages in 2 seconds
let messageTransfered = new HashMap();
let messageMemory = new HashMap();   // duplication check caused by pubsub in the case of abnormal disconnection
let scoreValue = new HashMap();   // duplication check for score

function requestReDirectMessage(requestId, query, userId, requestTime, conversationType) {  
    console.log('--> send the redirected message');
        
    if(messageTransfered.get(requestId)==undefined) {
        console.log('--> sendMessage: ', query);

        next = true;  // initiate valriable 'next' for audio play

        if(isReservedCommend(query)==false) {  // message            
            if(scoreValue.get(requestId)==undefined && isGame) { // check duplication
                console.log('get score for ', query);
                getScore(userId, requestId, query); 
                scoreValue.put(requestId, true);
            }

            sendMessage({
                "user_id": userId,
                "request_id": requestId,
                "request_time": requestTime,        
                "type": "text",
                "body": query,
                "convType": conversationType,
                "characterType": userName,
                "characterName": sender
            });
        }
        else {  // reservice commend
            actionforReservedCommend(requestId, query);
        }
        messageMemory.put(requestId, query);      
        messageTransfered.put(requestId, true);
                
        remainingRedirectedMessage = "";
    }        
}

function delayedRequestForRedirectionMessage(requestId, query, userId, requestTime, conversationType) {    
    console.log('--> start delay() of redirected message');

    remainingRedirectedMessage = {
        'timestr': requestTime,
        'requestId': requestId,
        'message': query
    }; 
    console.log('new remainingRedirectedMessage[message]: ', remainingRedirectedMessage['message']);

    redirectTm = setTimeout(function () {
        console.log('--> delayed request: ', query);
        console.log('messageTransfered[requestId] = ', messageTransfered.get(requestId));
        
        if(messageTransfered.get(requestId)==undefined) {
            console.log('--> sendMessage: ', query);

            next = true;  // initiate valriable 'next' for audio play        

            if(isReservedCommend(query)==false) {                
                if(scoreValue.get(requestId)==undefined && isGame) { // check duplication
                    console.log('get score for ', query);
                    getScore(userId, requestId, query); 
                    scoreValue.put(requestId, true);
                }

                sendMessage({
                    "user_id": userId,
                    "request_id": requestId,
                    "request_time": requestTime,        
                    "type": "text",
                    "body": query,
                    "convType": conversationType,
                    "characterType": userName,
                    "characterName": sender
                });
            }
            else {  // reservice commend
                actionforReservedCommend(requestId, query);
            }

            messageMemory.put(requestId, query);      
            messageTransfered.put(requestId, true);
                
            remainingRedirectedMessage = "";
        }
        
        clearRedirectTm();
    }, 2000);
}
function clearRedirectTm() {
    clearTimeout(redirectTm);
}

// voice session 
function voiceConnect(voiceEndpoint, type) {
    const ws_voice = new WebSocket(voiceEndpoint);

    // connection event
    ws_voice.onopen = function () {
        console.log('voice connected...');
        isVoiceConnected = true;

        // request initiation of redis
        let requestObj = {
            "user_id": userId,
            "type": "initiate"
        }
        voiceWebSocket.send(JSON.stringify(requestObj));
    
        if(type == 'initial')
            setInterval(voicePing, 40000);  // ping interval: 40 seconds
    };

    // message 
    ws_voice.onmessage = function (event) {     
        isVoiceConnected = true;   
        if (event.data.substr(1,8) == "__pong__") {
            console.log('<-voice pong');
            voicePong();
            return;
        }
        else {  // voice messages delivered from interpreter (device <-> trasncribe)
            response = JSON.parse(event.data)

             if(response.status == 'redirected') {  // voice message status == redirected
                feedback.style.display = 'none';      
                console.log('response: ', response);
                
                let msg = JSON.parse(response.msg)

                requestId = msg.requestId;
                query = msg.query;
                state = msg.state;

                type = msg.type;
                console.log('type: ', type);

                if(type == 'message') {
                    console.log('requestId: ', requestId);
                    console.log('query: ', query);
                    console.log('voice state: ', state);

                    let current = new Date();
                    let datastr = getDate(current);
                    let timestr = getTime(current);
                    let requestTime = datastr+' '+timestr;

                    console.log('remainingRedirectedMessage', remainingRedirectedMessage);    // last redirected message but not delivered

                    if(state=='completed') {
                        if (remainingRedirectedMessage && requestId != remainingRedirectedMessage['requestId']) {
                            requestId = remainingRedirectedMessage['requestId']; // use the remained requestId for display
                        
                            remainingRedirectedMessage['message'] = remainingRedirectedMessage['message']+'\n'+query; // add new message
                            query = remainingRedirectedMessage['message'];
                        }

                        if(messageMemory.get(requestId)==undefined) { 

                            addSentMessage(requestId, timestr, query);

                            if(enableDelayedMessage == false) {
                                requestReDirectMessage(requestId, query, userId, requestTime, conversationType)
                            }
                            else {  // in order to manipulate voice messages where the message will be delayed for one time
                                delayedRequestForRedirectionMessage(requestId, query, userId, requestTime, conversationType);                                   
                            }
                        }
                        else {  
                            console.log('ignore the duplicated message: ', query);
                        }                    
                    }
                    else {
                        addSentMessage(requestId, timestr, query);
                    }
                }
                else if(type == 'game') { // game event
                    console.log('state: ', state);

                    if(state == 'start') {
                        addNotifyMessage('start the game.');
                        console.log('start a game');

                        // To-DO: clear memory 
                        let current = new Date();
                        let datastr = getDate(current);
                        let timestr = getTime(current);
                        let requestTime = datastr+' '+timestr;
                        // addSentMessage(uuidv4(), timestr, 'clearMemory');
                        sendMessage({
                            "user_id": userId,
                            "request_id": uuidv4(),
                            "request_time": requestTime,        
                            "type": "text",
                            "body": 'clearMemory',
                            "convType": conversationType,
                            "characterType": userName,
                            "characterName": sender
                        })
                        console.log('clearMemory');
                        
                        initializeItems(userId)
                        console.log('initialize chat history');
                    }
                    else if (state == 'end') {
                        addNotifyMessage('end the game.');

                        console.log('initiate commend counter');
                        initCommendCounter();                   
                    }
                    else {
                        addNotifyMessage('game event: '+state);
                    }
                }
                else if(type == 'photo') { // photo event
                    console.log('state: ', state);

                    if(state == 'start-photo') {
                        addNotifyMessage('start in photo booth.');
                        console.log('start in photo booth');

                        /*
                        let current = new Date();
                        let datastr = getDate(current);
                        let timestr = getTime(current);
                        let requestTime = datastr+' '+timestr;
                        // addSentMessage(uuidv4(), timestr, 'clearMemory');

                        let requestId = uuidv4();
                        sendMessage({
                            "user_id": userId,
                            "request_id": requestId,
                            "request_time": requestTime,        
                            "type": "text",
                            "body": 'clearMemory',
                            "convType": conversationType,
                            "characterType": userName,
                            "characterName": sender
                        })
                        console.log('clearMemory');
                        
                        initializeItems(userId)
                        console.log('initialize chat history');
                        */

                        // play audio                        
                        console.log('speechType: ', speechType);
                        
                        let startMsg = "사진 찍으러 왔구나~ 방문을 환영해! 지금 어떤 기분인지 기념 사진을 남겨보자! 준비 됐지?";
                        if(speechType=='robot' || speechType=='both') {
                            if (silientMode==false) {
                                sendControl(userId, 'text', startMsg, "", 0, requestId);
                            }
                        }

                        if(speechType=='local' || speechType=='both') { // local
                            addReceivedMessage(requestId, startMsg);  
                            playAudioMessage(startMsg);
                        }
                    }
                    else if (state == 'end-photo') {
                        addNotifyMessage('end the game.');

                        console.log('initiate commend counter');
                        initCommendCounter();             
                                                
                        // play audio                        
                        console.log('speechType: ', speechType);
                        
                        let startMsg = "잘가! 즐거운 하루 보내!";
                        if(speechType=='robot' || speechType=='both') {
                            if (silientMode==false) {
                                sendControl(userId, 'text', startMsg, "", 0, requestId);
                            }
                        }

                        if(speechType=='local' || speechType=='both') { // local
                            addReceivedMessage(requestId, startMsg);  
                            playAudioMessage(startMsg);
                        }
                    }
                    else if(state == 'message') {
                        // play audio                        
                        console.log('speechType: ', speechType);
                        
                        let startMsg = "사진 찍으러 왔구나~ 방문을 환영해! 지금 어떤 기분인지 기념 사진을 남겨보자! 준비 됐지?";
                        if(speechType=='robot' || speechType=='both') {
                            if (silientMode==false) {
                                sendControl(userId, 'text', startMsg, "", 0, requestId);
                            }
                        }

                        if(speechType=='local' || speechType=='both') { // local
                            addReceivedMessage(requestId, startMsg);  
                            playAudioMessage(startMsg);
                        }
                    }
                }
                else if(type == 'broadcast') { // broadcast message
                    console.log('state: ', state);
                    console.log('speechType: ', speechType);

                    broadcastMsg = msg.query;
                    console.log('broadcastMsg: ', broadcastMsg);
                        
                    if(speechType=='robot' || speechType=='both') {
                        if (silientMode==false) {
                            sendControl(userId, 'text', broadcastMsg, "", 0, requestId);
                        }
                    }

                    if(speechType=='local' || speechType=='both') { // local
                        addReceivedMessage(requestId, broadcastMsg);  
                        playAudioMessage(broadcastMsg);
                    }
                }                            
            }      
            else if(response.status == 'error') {
                feedback.style.display = 'none';
                console.log('error: ', response.msg);
                addNotifyMessage(response.msg);
            }   
        }        
    };

    // disconnect
    ws_voice.onclose = function () {
        console.log('voice disconnected...!');
        isVoiceConnected = false;

        ws_voice.close();
        console.log('the voice session will be closed');
    };

    // error
    ws_voice.onerror = function (error) {
        console.log(error);
        isVoiceConnected = false;

        ws_voice.close();
        console.log('the voice session will be closed');
    };

    return ws_voice;
}

function playAudioMessage(text) {
    const uri = "speech";
    const xhr = new XMLHttpRequest();

    let speed = 120;
    let voiceId;
    let langCode;
    if(conversationType=='english') {
        langCode = 'en-US';
        voiceId = 'Ivy';
    }
    else {
        langCode = 'ko-KR';  // ko-KR en-US(영어)) ja-JP(일본어)) cmn-CN(중국어)) sv-SE(스페인어))
        voiceId = 'Seoyeon';
    }
    
    // voiceId: 'Aditi'|'Amy'|'Astrid'|'Bianca'|'Brian'|'Camila'|'Carla'|'Carmen'|'Celine'|'Chantal'|'Conchita'|'Cristiano'|'Dora'|'Emma'|'Enrique'|'Ewa'|'Filiz'|'Gabrielle'|'Geraint'|'Giorgio'|'Gwyneth'|'Hans'|'Ines'|'Ivy'|'Jacek'|'Jan'|'Joanna'|'Joey'|'Justin'|'Karl'|'Kendra'|'Kevin'|'Kimberly'|'Lea'|'Liv'|'Lotte'|'Lucia'|'Lupe'|'Mads'|'Maja'|'Marlene'|'Mathieu'|'Matthew'|'Maxim'|'Mia'|'Miguel'|'Mizuki'|'Naja'|'Nicole'|'Olivia'|'Penelope'|'Raveena'|'Ricardo'|'Ruben'|'Russell'|'Salli'|'Seoyeon'|'Takumi'|'Tatyana'|'Vicki'|'Vitoria'|'Zeina'|'Zhiyu'|'Aria'|'Ayanda'|'Arlet'|'Hannah'|'Arthur'|'Daniel'|'Liam'|'Pedro'|'Kajal'|'Hiujin'|'Laura'|'Elin'|'Ida'|'Suvi'|'Ola'|'Hala'|'Andres'|'Sergio'|'Remi'|'Adriano'|'Thiago'|'Ruth'|'Stephen'|'Kazuha'|'Tomoko'

    // Aditi: neural is not support
    // Amy: good
    // Astrid: neural is not support
    // Bianca: 스페인어? (x)
    // Brian: 
    // Camila (o)
   
    if(conversationType == 'translation') {
        langCode = langCode;
        voiceId = voiceId; // child Ivy, adult Joanna
        speed = '120';
    }    
    console.log('voiceId: ', voiceId);
    
    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            response = JSON.parse(xhr.responseText);
            // console.log("response: ", response);

            playAudioLine(response.body);        

            console.log('successfully played. text= '+text);
        }
    };
    
    var requestObj = {
        "text": text,
        "voiceId": voiceId,
        "langCode": langCode,
        "speed": speed
    }
    // console.log("request: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);            
}

let audioData = new HashMap();
function loadAudio(requestId, text) {
    const uri = "speech";
    const xhr = new XMLHttpRequest();

    let speed = 120;
    let voiceId;
    let langCode;
    if(conversationType=='english') {
        langCode = 'en-US';
        voiceId = 'Ivy';
    }
    else {
        langCode = 'ko-KR';  // ko-KR en-US(영어)) ja-JP(일본어)) cmn-CN(중국어)) sv-SE(스페인어))
        voiceId = 'Seoyeon';
    }
    
    // voiceId: 'Aditi'|'Amy'|'Astrid'|'Bianca'|'Brian'|'Camila'|'Carla'|'Carmen'|'Celine'|'Chantal'|'Conchita'|'Cristiano'|'Dora'|'Emma'|'Enrique'|'Ewa'|'Filiz'|'Gabrielle'|'Geraint'|'Giorgio'|'Gwyneth'|'Hans'|'Ines'|'Ivy'|'Jacek'|'Jan'|'Joanna'|'Joey'|'Justin'|'Karl'|'Kendra'|'Kevin'|'Kimberly'|'Lea'|'Liv'|'Lotte'|'Lucia'|'Lupe'|'Mads'|'Maja'|'Marlene'|'Mathieu'|'Matthew'|'Maxim'|'Mia'|'Miguel'|'Mizuki'|'Naja'|'Nicole'|'Olivia'|'Penelope'|'Raveena'|'Ricardo'|'Ruben'|'Russell'|'Salli'|'Seoyeon'|'Takumi'|'Tatyana'|'Vicki'|'Vitoria'|'Zeina'|'Zhiyu'|'Aria'|'Ayanda'|'Arlet'|'Hannah'|'Arthur'|'Daniel'|'Liam'|'Pedro'|'Kajal'|'Hiujin'|'Laura'|'Elin'|'Ida'|'Suvi'|'Ola'|'Hala'|'Andres'|'Sergio'|'Remi'|'Adriano'|'Thiago'|'Ruth'|'Stephen'|'Kazuha'|'Tomoko'

    // Aditi: neural is not support
    // Amy: good
    // Astrid: neural is not support
    // Bianca: 스페인어? (x)
    // Brian: 
    // Camila (o)
   
    if(conversationType == 'translation') {
        langCode = langCode;
        voiceId = voiceId; // child Ivy, adult Joanna
        speed = '120';
    }    
    // console.log('voiceId: ', voiceId);
    
    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            response = JSON.parse(xhr.responseText);
            // console.log("response: ", response);

            audioData[requestId+text] = response.body;

            // console.log('successfully loaded. text= '+text);
            // console.log(response.body);
            // console.log(audioData[requestId+text]);
        }
    };
    
    var requestObj = {
        "text": text,
        "voiceId": voiceId,
        "langCode": langCode,
        "speed": speed
    }
    // console.log("request: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);            
} 

function playAudioList() {
    // console.log('next = '+next+', playList: '+playList.length);
    
    for(let i=0; i<playList.length;i++) {
        // console.log('audio data--> ', audioData[requestId+playList[i].text])
        // console.log('playList: ', playList);

        if(next == true && playList[i].played == false && requestId == playList[i].requestId && audioData[requestId+playList[i].text]) {
            // console.log('[play] '+i+': '+requestId+', text: '+playList[i].text);
            playId = i;
            playAudioLine(audioData[requestId+playList[i].text]);            

            next = false;
            break;
        }
        else if(requestId != playList[i].requestId) {
            playList[i].played = true;
        }
    }
}

async function playAudioLine(audio_body){    
    var sound = "data:audio/ogg;base64,"+audio_body;
    
    var audio = document.querySelector('audio');
    audio.src = sound;
    
    // console.log('play audio');

    await playAudio(audio)
}

// audio play
var audio = document.querySelector('audio');
audio.addEventListener("ended", function() {
    console.log("playId: ", playId)

    if(playList[playId] != undefined) {
        console.log("played audio: ", playList[playId].text)

        delay(1000)

        next = true;
        playList[playId].played = true;
        audioData.remove([requestId+playList[playId].text]);

        playAudioList()
    }        
    else {
        playList = [];
        playId = 0;
    }
});

function playAudio(audio) {
    return new Promise(res=>{
        audio.play()
        audio.onended = res
    })
}

// Documents
const title = document.querySelector('#title');
const sendBtn = document.querySelector('#sendBtn');
const message = document.querySelector('#chatInput')
const chatPanel = document.querySelector('#chatPanel');

let profileImage = document.getElementById('profileImage');

let isResponsed = new HashMap();
let indexList = new HashMap();
let retryNum = new HashMap();

// message log list
let msglist = [];
let maxMsgItems = 200;
let maxLengthOfHistoryReadable = maxMsgItems/4;
let msgHistory = new HashMap();
let callee = "AWS";
let index=0;

let conversationType = localStorage.getItem('convType'); // set convType if exists 
if(conversationType=="") {
    conversationType = "normal";
}
console.log('conversationType: ', conversationType);

let isGame = true;
if(conversationType=='normal' || conversationType=='english') {
    isGame = false;
}
console.log('isGame: ', isGame);

initiate();

function initiate() {
    for (i=0;i<maxMsgItems;i++) {
        msglist.push(document.getElementById('msgLog'+i));
    
        // add listener        
        (function(index) {
            msglist[index].addEventListener("click", function() {
                if(msglist.length < maxMsgItems) i = index;
                else i = index + maxMsgItems;
    
                console.log('click! index: '+index);
            })
        })(i);
    }

    if (userName == 'Maltese') {
        calleeName.textContent = "베드락";          
    }
    else if (userName == 'WelshCorgi') {
        calleeName.textContent = "람다";  
    }
    else if (userName == 'Chihuahua') {
        calleeName.textContent = "폴리";  
    }
    else if (userName == 'Jindogae') {
        calleeName.textContent = "그린그래스";  
    }
    else if (userName == 'Poodle') {
        calleeName.textContent = "에스3";  
    }
    else if (userName == 'Schnauzer') {
        calleeName.textContent = "다이나모";  
    }
    else if (userName == 'Pug') {
        calleeName.textContent = "아이엠";  
    }
    else if (userName == 'Shepherd') {
        calleeName.textContent = "세이지메이커";  
    }
    else {
        calleeName.textContent = "AWS";  
    }
    sender = calleeName.textContent;
    profileImage.src = userName+".jpg";

    if(langstate=='korean') {
        addNotifyMessage("Amazon Bedrock을 이용하여 채팅을 시작합니다.");
        addReceivedMessage(uuidv4(), "안녕하세요. Robo SoleMate와 즐거운 대화를 시작합니다.")
    }
    else {
        addNotifyMessage("Start chat with Amazon Bedrock");             
        addReceivedMessage(uuidv4(), "Welcome! Enjoy this conversation with Robo SoleMate.")            
    }

    getHistory(userId, 'initiate');
}

// Listeners
message.addEventListener('keyup', function(e){
    if (e.keyCode == 13) {
        onSend(e);
    }
});

// refresh button
refreshChatWindow.addEventListener('click', function(){
    console.log('go back user input menu');
    window.location.href = "index.html";
});

// depart button
depart.addEventListener('click', function(){
    console.log('depart icon');
    
    deleteItems(userId);    
});

function updateChatHistory() {
    for(let i=0;i<maxMsgItems;i++) {
        msglist[i].innerHTML = `<div></div>`
    }
    
    msglist = [];
    index = 0;

    indexList = new HashMap();

    for (i=0;i<maxMsgItems;i++) {
        msglist.push(document.getElementById('msgLog'+i));
    
        // add listener        
        (function(index) {
            msglist[index].addEventListener("click", function() {
                if(msglist.length < maxMsgItems) i = index;
                else i = index + maxMsgItems;
    
                console.log('click! index: '+index);
            })
        })(i);
    } 

    getHistory(userId, 'update');    
    // window.location.href = "chat.html";
}

sendBtn.addEventListener('click', onSend);
function onSend(e) {
    e.preventDefault();

    if(message.value != '') {
        console.log("msg: ", message.value);

        let current = new Date();
        let datastr = getDate(current);
        let timestr = getTime(current);
        let requestTime = datastr+' '+timestr

        let requestId = uuidv4();
        addSentMessage(requestId, timestr, message.value);

        if(protocol == 'WEBSOCKET') {
            if(isReservedCommend(message.value)==false) {                   
                if(isGame) {
                    console.log('request to estimate the score');
                    getScore(userId, requestId, message.value);     
                }

                sendMessage({
                    "user_id": userId,
                    "request_id": requestId,
                    "request_time": requestTime,        
                    "type": "text",
                    "body": message.value,
                    "convType": conversationType,
                    "characterType": userName,
                    "characterName": sender
                })
                console.log('characterType: ', userName);
                console.log('characterName' , sender);
            }
            else {  // reservice commend
                actionforReservedCommend(requestId, message.value);
            }
        }
        else {
            sendRequest(message.value, requestId, requestTime);
        }       
    }
    message.value = "";

    chatPanel.scrollTop = chatPanel.scrollHeight;  // scroll needs to move bottom
}

// UUID 
function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

(function() {
    window.addEventListener("focus", function() {
        // console.log("Back to front");

        // if(msgHistory.get(callee))
        //    updateCallLogToDisplayed();
    })
})();

function getDate(current) {    
    return current.toISOString().slice(0,10);
}

function getTime(current) {
    let time_map = [current.getHours(), current.getMinutes(), current.getSeconds()].map((a)=>(a < 10 ? '0' + a : a));
    return time_map.join(':');
}

function addSentMessage(requestId, timestr, text) {
    let idx = index;

    if(!indexList.get(requestId+':send')) {
        indexList.put(requestId+':send', idx);

        index++;
    }
    else {
        idx = indexList.get(requestId+':send');
        // console.log("reused index="+idx+', id='+requestId+':send');        
    }
    // console.log("index (sendMessage):", idx);   

    let length = text.length;    
    // console.log('length: ', length);
    if(length < 10) {
        msglist[idx].innerHTML = 
            `<div class="chat-sender20 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;   
    }
    else if(length < 14) {
        msglist[idx].innerHTML = 
            `<div class="chat-sender25 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;   
    }
    else if(length < 17) {
        msglist[idx].innerHTML = 
            `<div class="chat-sender30 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;
    }  
    else if(length < 21) {
        msglist[idx].innerHTML = 
            `<div class="chat-sender35 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;
    }
    else if(length < 26) {
        msglist[idx].innerHTML = 
            `<div class="chat-sender40 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;
    }
    else if(length < 35) {
        msglist[idx].innerHTML = 
            `<div class="chat-sender50 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;
    }
    else if(length < 80) {
        msglist[idx].innerHTML = 
            `<div class="chat-sender60 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;
    }  
    else if(length < 145) {
        msglist[idx].innerHTML = 
            `<div class="chat-sender70 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;
    }  
    else {
        msglist[idx].innerHTML = 
            `<div class="chat-sender80 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;
    }     

    chatPanel.scrollTop = chatPanel.scrollHeight;  // scroll needs to move bottom
}       

function addSentMessageForSummary(requestId, timestr, text) {  
    let idx = index;
    console.log("sent message: "+text);

    if(!indexList.get(requestId+':send')) {
        indexList.put(requestId+':send', idx);

        index++;
    }
    else {
        idx = indexList.get(requestId+':send');
        console.log("reused index="+idx+', id='+requestId+':send');        
    }
    console.log("index (sendMessage):", idx);   

    let length = text.length;
    if(length < 100) {
        msglist[idx].innerHTML = 
            `<div class="chat-sender60 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;   
    }
    else {
        msglist[idx].innerHTML = 
            `<div class="chat-sender80 chat-sender--right"><h1>${timestr}</h1>${text}&nbsp;<h2 id="status${idx}"></h2></div>`;
    }   

    chatPanel.scrollTop = chatPanel.scrollHeight;  // scroll needs to move bottom
}  

function sendControl(thingName, type, message, commend, score, requestId) {
    const uri = "control";
    const xhr = new XMLHttpRequest();

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            response = JSON.parse(xhr.responseText);
            // console.log("response: " + JSON.stringify(response));
        }
        else if(xhr.readyState ===4 && xhr.status === 504) {
            console.log("response: " + xhr.readyState + ', xhr.status: '+xhr.status);
        }
    };

    let requestObj;
    if(type == 'text') { // text
        requestObj = {
            "user_id": thingName,
            "request_id": requestId,
            "type": type,
            "message": message
        }
    }
    else if(type == 'commend') { // reserved commend
        requestObj = {
            "user_id": thingName,
            "request_id": requestId,
            "type": type,
            "commend": commend
        }
    }
    else { // score
        requestObj = {            
            "user_id": thingName,
            "request_id": requestId,
            "type": type,            
            "score":score
        }
    }
    
    // console.log("sendControl: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);            
}

function sendMessageToScoreBoard(thingName, type, message, requestId) {
    const uri = "score_chat";
    const xhr = new XMLHttpRequest();

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            response = JSON.parse(xhr.responseText);
            // console.log("response: " + JSON.stringify(response));
        }
        else if(xhr.readyState ===4 && xhr.status === 504) {
            // console.log("response: " + xhr.readyState + ', xhr.status: '+xhr.status);
        }
    };

    let requestObj;
    requestObj = {
        "user_id": thingName,
        "request_id": requestId,
        "type": type,
        "text": message
    }    
    // console.log("sendMessageToScoreBoard: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);            
}

function getScore(userId, requestId, text) {
    const uri = "score";
    const xhr = new XMLHttpRequest();

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            console.log("response: " + JSON.stringify(response));   
            let result = response.result;
            console.log("result: " + JSON.stringify(result));   
            let score = result.score;
            console.log("score: " + score);    
            let description = result.description;
            console.log("description: " + description);    

            //addNotifyMessage('[debug] score: '+score+', description: '+description);
            addNotifyMessage('Score: '+score+'점, ('+description+')');
            
            if(speechType=='robot' || speechType=='both') {
                sendControl(userId, "action", "", "", score, requestId)
            }   
        }
    };

    let mbti;
    if(conversationType=='normal' || conversationType=='english' || conversationType=='translation') mbti = 'ISTP';
    else mbti = conversationType;
    console.log('mbti: ', mbti);

    var requestObj = {
        "userId": userId,
        "requestId": requestId,
        "text": text,
        "mbti": mbti
    }
    console.log("request for getScore: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);   
}

function addReceivedMessage(requestId, msg) {
    let idx = index;

    // console.log("add received message: "+msg);
    if(!indexList.get(requestId+':receive')) {
        indexList.put(requestId+':receive', idx);
        index++;
    }
    else {
        idx = indexList.get(requestId+':receive');
        // console.log("reused index="+idx+', id='+requestId+':receive');        
    }
    // console.log("index (receiveMessage):", idx);   

    msg = msg.replaceAll("\n", "<br/>");

    var length = msg.length;
    // console.log('msg: ', msg)
    // console.log("length: ", length);

    if(length < 10) {
        msglist[idx].innerHTML = `<div class="chat-receiver20 chat-receiver--left"><h1>${sender}</h1>${msg}&nbsp;</div>`;  
    }
    else if(length < 14) {
        msglist[idx].innerHTML = `<div class="chat-receiver25 chat-receiver--left"><h1>${sender}</h1>${msg}&nbsp;</div>`;  
    }
    else if(length < 17) {
        msglist[idx].innerHTML = `<div class="chat-receiver30 chat-receiver--left"><h1>${sender}</h1>${msg}&nbsp;</div>`;  
    }
    else if(length < 21) {
        msglist[idx].innerHTML = `<div class="chat-receiver35 chat-receiver--left"><h1>${sender}</h1>${msg}&nbsp;</div>`;  
    }
    else if(length < 25) {
        msglist[idx].innerHTML = `<div class="chat-receiver40 chat-receiver--left"><h1>${sender}</h1>${msg}&nbsp;</div>`;  
    }
    else if(length < 35) {
        msglist[idx].innerHTML = `<div class="chat-receiver50 chat-receiver--left"><h1>${sender}</h1>${msg}&nbsp;</div>`;  
    }
    else if(length < 80) {
        msglist[idx].innerHTML = `<div class="chat-receiver60 chat-receiver--left"><h1>${sender}</h1>${msg}&nbsp;</div>`;  
    }
    else if(length < 145) {
        msglist[idx].innerHTML = `<div class="chat-receiver70 chat-receiver--left"><h1>${sender}</h1>${msg}&nbsp;</div>`;  
    }
    else {
        msglist[idx].innerHTML = `<div class="chat-receiver80 chat-receiver--left"><h1>${sender}</h1>${msg}&nbsp;</div>`;  
    }

    chatPanel.scrollTop = chatPanel.scrollHeight;  // scroll needs to move bottom    
}

function addNotifyMessage(msg) {
    // console.log("index:", index);   

    msglist[index].innerHTML =  
        `<div class="notification-text">${msg}</div>`;     

    index++;

    chatPanel.scrollTop = chatPanel.scrollHeight;  // scroll needs to move bottom
}

refreshChatWindow.addEventListener('click', function(){
    console.log('update chat window');
    // updateChatWindow(callee);
});

attachFile.addEventListener('click', function(){
    console.log('click: attachFile');

    let input = $(document.createElement('input')); 
    input.attr("type", "file");
    input.trigger('click');    
    
    $(document).ready(function() {
        input.change(function(evt) {
            var input = this;
            var url_file = $(this).val();
            var ext = url_file.substring(url_file.lastIndexOf('.') + 1).toLowerCase();
            var filename = url_file.substring(url_file.lastIndexOf('\\') + 1).toLowerCase();

            console.log('url: ' + url_file);
            console.log('filename: ' + filename);
            console.log('ext: ' + ext);

            if(ext == 'pdf') {
                contentType = 'application/pdf'           
            }
            else if(ext == 'txt') {
                contentType = 'text/plain'
            }
            else if(ext == 'csv') {
                contentType = 'text/csv'
            }
            else if(ext == 'ppt') {
                contentType = 'application/vnd.ms-powerpoint'
            }
            else if(ext == 'pptx') {
                contentType = 'application/vnd.ms-powerpoint'
            }
            else if(ext == 'doc' || ext == 'docx') {
                contentType = 'application/msword'
            }
            else if(ext == 'xls') {
                contentType = 'application/vnd.ms-excel'
            }
            else if(ext == 'py') {
                contentType = 'application/x-python-code'
            }
            else if(ext == 'js') {
                contentType = 'application/javascript'
            }
            else if(ext == 'md') {
                contentType = 'text/markdown'
            }
            else if(ext == 'png') {
                contentType = 'image/png'
            }
            else if(ext == 'jpeg' || ext == 'jpg') {
                contentType = 'image/jpeg'
            }

            let current = new Date();
            let datastr = getDate(current);
            let timestr = getTime(current);
            let requestTime = datastr+' '+timestr
            let requestId = uuidv4();

            let commend = message.value;
            console.log('commend: ', commend)
            if((ext == 'png' || ext == 'jpeg' || ext == 'jpg') && commend!="") {
                addSentMessageForSummary(requestId, timestr, message.value+"<br>"+"uploading the selected file in order to summerize...");

                message.value = "";
            }
            else {
                addSentMessageForSummary(requestId, timestr, "uploading the selected file in order to summerize...");
            }

            const uri = "upload";
            const xhr = new XMLHttpRequest();
        
            xhr.open("POST", uri, true);
            xhr.onreadystatechange = () => {
                if (xhr.readyState === 4 && xhr.status === 200) {
                    response = JSON.parse(xhr.responseText);
                    console.log("response: " + JSON.stringify(response));
                                        
                    // upload the file
                    const body = JSON.parse(response.body);
                    console.log('body: ', body);

                    const uploadURL = body.UploadURL;                    
                    console.log("UploadURL: ", uploadURL);

                    var xmlHttp = new XMLHttpRequest();
                    xmlHttp.open("PUT", uploadURL, true);       

                    //let formData = new FormData();
                    //formData.append("attachFile" , input.files[0]);
                    //console.log('uploading file info: ', formData.get("attachFile"));

                    const blob = new Blob([input.files[0]], { type: contentType });

                    xmlHttp.onreadystatechange = function() {
                        if (xmlHttp.readyState == XMLHttpRequest.DONE && xmlHttp.status == 200 ) {
                            console.log(xmlHttp.responseText);

                            sendMessage({
                                "user_id": userId,
                                "request_id": requestId,
                                "request_time": requestTime,
                                "type": "document",
                                "body": filename,
                                "commend": commend,
                                "convType": conversationType,
                                "characterType": userName,
                                "characterName": sender
                            })                                                        
                        }
                        else if(xmlHttp.readyState == XMLHttpRequest.DONE && xmlHttp.status != 200) {
                            console.log('status' + xmlHttp.status);
                            alert("Try again! The request was failed.");
                        }
                    };
        
                    xmlHttp.send(blob); 
                    // xmlHttp.send(formData); 
                    console.log(xmlHttp.responseText);
                }
            };
        
            var requestObj = {
                "type": "doc",
                "filename": filename,
                "contentType": contentType,
            }
            console.log("request from file: " + JSON.stringify(requestObj));
        
            var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});
        
            xhr.send(blob);       
        });
    });
       
    return false;
});

function sendRequest(text, requestId, requestTime) {
    const uri = "chat";
    const xhr = new XMLHttpRequest();

    isResponsed.put(requestId, false);
    retryNum.put(requestId, 12); // max 60s (5x12)

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            response = JSON.parse(xhr.responseText);
            console.log("response: " + JSON.stringify(response));
            
            addReceivedMessage(response.request_id, response.msg)
        }
        else if(xhr.readyState ===4 && xhr.status === 504) {
            console.log("response: " + xhr.readyState + ', xhr.status: '+xhr.status);

            getResponse(requestId);
        }
    };

    var requestObj = {
        "user_id": userId,
        "request_id": requestId,
        "request_time": requestTime,
        "type": "text",
        "body":text
    }
    console.log("request for query: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);            
}

function sendRequestForSummary(object, requestId, requestTime) {
    const uri = "chat";
    const xhr = new XMLHttpRequest();

    isResponsed.put(requestId, false);
    retryNum.put(requestId, 60); // max 300s (5x60)

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            response = JSON.parse(xhr.responseText);
            console.log("response: " + JSON.stringify(response));
            
            addReceivedMessage(response.request_id, response.msg)
        }
        else if(xhr.readyState ===4 && xhr.status === 504) {
            console.log("response: " + xhr.readyState + ', xhr.status: '+xhr.status);

            getResponse(requestId);
        }
        else {
            console.log("response: " + xhr.readyState + ', xhr.status: '+xhr.status);
        }
    };
    
    var requestObj = {
        "user_id": userId,
        "request_id": requestId,
        "request_time": requestTime,
        "type": "document",
        "body": object
    }
    console.log("request: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);            
}

function delay(ms = 1000) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
async function getResponse(requestId) {
    await delay(5000);
    
    let n = retryNum.get(requestId);
    if(n == 0) {
        console.log('Failed!')
        return;
    }
    else {
        console.log('Retry!');
        retryNum.put(requestId, n-1);
        sendRequestForRetry(requestId);
    }    
}

function sendRequestForRetry(requestId) {
    const uri = "query";
    const xhr = new XMLHttpRequest();

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            response = JSON.parse(xhr.responseText);
            console.log("response: " + JSON.stringify(response));
                        
            if(response.msg) {
                isResponsed.put(response.request_id, true);
                addReceivedMessage(response.request_id, response.msg);        
                
                console.log('completed!');
            }            
            else {
                console.log('The request is not completed yet.');

                getResponse(requestId);
            }
        }
    };
    
    var requestObj = {
        "request_id": requestId,
    }
    console.log("request: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);            
}

function getHistory(userId, state) {
    const uri = "history";
    const xhr = new XMLHttpRequest();

    let allowTime = getAllowTime();

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            let history = JSON.parse(response['msg']);
            // console.log("history: " + JSON.stringify(history));

            let start = 0;
            if(history.length > maxLengthOfHistoryReadable) {
                index = 0;
                start = history.length - maxLengthOfHistoryReadable;
            }

            // console.log('history length of dynamodb: ', history.length);
            // console.log('start position of history: ', start)

            for(let i=start; i<history.length; i++) {
                if(history[i].type=='text') {                
                    // let timestr = history[i].request_time.substring(11, 19);
                    let requestId = history[i].request_id;
                    // console.log("requestId: ", requestId);
                    let timestr = history[i].request_time;
                    // console.log("timestr: ", timestr);
                    let body = history[i].body;
                    // console.log("question: ", body);
                    let msg = history[i].msg;
                    // console.log("answer: ", msg);

                    addSentMessage(requestId, timestr, body)
                    addReceivedMessage(requestId, msg);                            
                }                 
            }
            
         /*   if(history.length>=1 && state=='initiate') {
                if(langstate=='korean') {
                    addNotifyMessage("대화를 다시 시작하였습니다.");
                }
                else {
                    addNotifyMessage("Welcome back to the conversation");                               
                }                
            } */

            chatPanel.scrollTop = chatPanel.scrollHeight;  // scroll needs to move bottom
        }
    };
    
    var requestObj = {
        "userId": userId,
        "allowTime": allowTime
    }
    console.log("request: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);            
}

function deleteItems(userId) {
    const uri = "delete";
    const xhr = new XMLHttpRequest();

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            console.log("response: " + JSON.stringify(response));

            window.location.href = "index.html";
        }
    };
    
    var requestObj = {
        "userId": userId
    }
    console.log("request: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);            
}

function initializeItems(userId) {
    const uri = "delete";
    const xhr = new XMLHttpRequest();

    xhr.open("POST", uri, true);
    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            console.log("response: " + JSON.stringify(response));

            window.location.href = "chat.html";
        }
    };
    
    var requestObj = {
        "userId": userId
    }
    console.log("request: " + JSON.stringify(requestObj));

    var blob = new Blob([JSON.stringify(requestObj)], {type: 'application/json'});

    xhr.send(blob);            
}

function getAllowTime() {    
    let allowableDays = 2; // two day's history
    
    let current = new Date();
    let allowable = new Date(current.getTime() - 24*60*60*1000*allowableDays);  
    let allowTime = getDate(allowable)+' '+getTime(current);
    console.log('Current Time: ', getDate(current)+' '+getTime(current));
    console.log('Allow Time: ', allowTime);
    
    return allowTime;
}
