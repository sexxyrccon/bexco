#include <Servo.h>

Servo servo1;
Servo servo2;

int motor1 = 3; //left
int motor2 = 4; //right

int input_data;

void setup() {
  // 서보 모터와 시리얼 초기화
  Serial.begin(4800);
}

void loop() {
  // 시리얼 데이터가 있는지 확인
  while (Serial.available()) {
    input_data = Serial.read(); // 한 문자씩 읽기
    Serial.println(input_data);

      // 다음 입력을 위해 인덱스 초기화
    
  }
}
