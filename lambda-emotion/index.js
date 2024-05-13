const aws = require('aws-sdk');
const { v4: uuidv4 } = require('uuid');
const s3 = new aws.S3();
const bucketName = process.env.bucketName;
const collectionId = process.env.collectionId;

const dynamoDB = new aws.DynamoDB.DocumentClient();

exports.handler = async (event, context) => {
    // console.log('## ENVIRONMENT VARIABLES: ' + JSON.stringify(process.env));
    // console.log('## EVENT: ' + JSON.stringify(event))

    const body = Buffer.from(event["body"], "base64");
    // console.log('body: ' + body)
    const header = event['multiValueHeaders'];
    // console.log('header: ' + JSON.stringify(header));

    let contentType;
    if (header['content-type']) {
        contentType = String(header['content-type']);
    }
    if (header['Content-Type']) {
        contentType = String(header['Content-Type']);
    }
    // console.log('contentType = '+contentType);    

    let userId;
    if (header['X-user-id']) {
        userId = String(header['X-user-id']);
    }
    else {
        userId = uuidv4();
    }

    const fileName = 'profile/' + userId + '.jpeg';
    // console.log('fileName = '+fileName);

    try {
        const destparams = {
            Bucket: bucketName,
            Key: fileName,
            Body: body,
            ContentType: contentType
        };

        //  console.log('destparams: ' + JSON.stringify(destparams));
        const { putResult } = await s3.putObject(destparams).promise();

        // console.log('### finish upload: ' + userId);
    } catch (error) {
        console.log(error);
        return;
    }

    let response = "";
    let isCompleted = false;
    try {
        // console.log('**start emotion detection');
        const rekognition = new aws.Rekognition();
        const rekognitionParams = {
            Image: {
                S3Object: {
                    Bucket: bucketName,
                    Name: fileName
                },
            },
            Attributes: ['ALL']
        };
        // console.log('rekognitionParams = '+JSON.stringify(rekognitionParams))

        const detectResponse = await rekognition.detectFaces(rekognitionParams).promise();
        console.log('data: '+JSON.stringify(detectResponse));

        if (detectResponse['FaceDetails'][0]) {

            // search the face for identification
            let faceId;

            try {
                const indexFacesParams = {
                    CollectionId: collectionId,
                    Image: {
                        S3Object: {
                            Bucket: bucketName,
                            Name: fileName
                        },
                    },
                };
                // console.log('rekognitionParams = '+JSON.stringify(indexFacesParams))
                const indexResponse = await rekognition.indexFaces(indexFacesParams).promise();
                console.log('data: '+JSON.stringify(indexResponse));
                
                
                // const primaryFaceId = indexResponse.FaceRecords[0]?.Face.FaceId; // 첫 번째 얼굴의 FaceId
                const faceDetails = indexResponse.FaceRecords.map((record, index) => {
                    const detail = {
                        id: record.Face.FaceId,
                        key: fileName,
                        name: record.Face.FaceId, 
                        bucket: bucketName,
                        age: calculateMiddleAge(detectResponse.FaceDetails[index].AgeRange),
                        emotions: detectResponse.FaceDetails[index].Emotions[0].Type,
                        smile: detectResponse.FaceDetails[index].Smile.Value,
                        eyeglasses: detectResponse.FaceDetails[index].Eyeglasses.Value,
                        sunglasses: detectResponse.FaceDetails[index].Sunglasses.Value,
                        gender: detectResponse.FaceDetails[index].Gender.Value,
                        beard: detectResponse.FaceDetails[index].Beard.Value,
                        mustache: detectResponse.FaceDetails[index].Mustache.Value,
                        eyesOpen: detectResponse.FaceDetails[index].EyesOpen.Value,
                        mouthOpen: detectResponse.FaceDetails[index].MouthOpen.Value,
                        generation: determineGeneration(calculateMiddleAge(detectResponse.FaceDetails[index].AgeRange)),
                        time: formatLocalDate(),
                        createdAt: new Date(new Date().getTime() + 9 * 3600 * 1000).toISOString()
                    };
                    return detail;
                });

                await Promise.all(faceDetails.map(face => {
                    const params = {
                        TableName: "EmotionDetailInfo-3d2nq2n4sfcqnfelmjj3n3ycje-dev",
                        Item: face
                    };
                    return dynamoDB.put(params).promise();
                }));
                
                const emotionInfo = {
                    key: fileName
                };
                console.info('emotionInfo: ' + JSON.stringify(emotionInfo));
            
                response = {
                    statusCode: 200,
                    body: JSON.stringify(emotionInfo)
                };
            } catch (err) {
                console.log(err);
            }
        }
        else {
            response = {
                statusCode: 404,
                body: "No Face"
            };
        }

        isCompleted = true;
    } catch (error) {
        console.log(error);

        response = {
            statusCode: 500,
            body: error
        };
    }
    
    function calculateMiddleAge(ageRange) {
        let ageRangeLow = ageRange.Low;
        let ageRangeHigh = ageRange.High;
        return (ageRangeLow + ageRangeHigh) / 2;
    }
    
    function determineGeneration(middleAge) {
        if (middleAge <= 5) return 'toddler'; // 유아
        else if (middleAge <= 12) return 'child'; // 아동
        else if (middleAge <= 18) return 'teenager'; // 청소년
        else if (middleAge <= 25) return 'young-adult'; // 청년
        else if (middleAge <= 49) return 'adult'; // 중년
        else if (middleAge <= 64) return 'middle-age'; // 장년
        else if (middleAge >= 65) return 'elder'; // 노년

    }
    
    function formatLocalDate() {
        const offset = 9; // UTC+9 for KST
        const now = new Date(new Date().getTime() + offset * 3600 * 1000);
        return now.toISOString().replace(/T/, ' ').replace(/\..+/, '');
}
    
    function wait() {
        return new Promise((resolve, reject) => {
            if (!isCompleted) {
                setTimeout(() => resolve("wait..."), 1000);
            }
            else {
                setTimeout(() => resolve("done..."), 0);
            }
        });
    }
    console.log(await wait());
    console.log(await wait());
    console.log(await wait());
    console.log(await wait());
    console.log(await wait());

    console.debug('emotion response: ' + JSON.stringify(response));
    return response;
};


