# 대표하는 남여 이미지 생성

데모를 방문하는 사람들의 남/여, 연령등의 정보를 활용하여 대표하는 남여 이미지를 생성합니다.

## 저장 및 활용

저장소의 '/dashboard' 폴더에 "representative_man.jpeg"와 "representative_weman"으로 이미지를 생성한 후에, Dashboard에서 활용합니다.

## 이미지 생성 방법

1) DynamoDB에서 아래와 같은 정보를 추출합니다. 

2) 15분 간격으로 아래 Prompt를 이용하여 이미지를 생성합닏.

- Man의 Prompt 예제
```text
The face of a Korean man in his early 30s. A face that smiles 80 percent of the time. No glasses, eyes open, 75 percent of the time. his emotion is mainly Calm. He loves puppy and IT Technology.
```

- Weman의 Prompt 예제

```text  
The face of a Korean woman in her early 30s. A face that smiles 80 percent of the time. No glasses, eyes open, 75 percent of the time. her emotion is mainly Calm. She loves puppy and IT Technology and K-beauty. (edited)
```

3) 파일은 항상 동일한 이름으로 overwrite 합니다. 이것은 Dashboad에서 고정 url으로 Dashboard에 접근하기 위함입니다.

