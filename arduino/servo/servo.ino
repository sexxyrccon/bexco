#include <Servo.h>
#include <stdlib.h>

Servo servo1;
Servo servo2;

int motor1 = 3; //left
int motor2 = 4; //right

String input_data = ""; // 입력 데이터를 저장할 문자열

void setup() {
  // 서보 모터와 시리얼 초기화
  Serial.begin(9600);
  servo1.attach(motor1);
  servo2.attach(motor2);
}

void loop() {
  // 시리얼 데이터가 있는지 확인
  while (Serial.available()) {
    char incomingByte = Serial.read(); // 한 문자씩 읽기

    // 줄바꿈 문자가 들어오면 전체 문자열 처리
    if (incomingByte == '\n') {
      if (input_data.length() == 6) {
        // 첫 3자리와 마지막 3자리를 분리
        String left_str = input_data.substring(0, 3);
        String right_str = input_data.substring(3, 6);

        // 문자열을 정수로 변환
        int left_angle = left_str.toInt();
        int right_angle = right_str.toInt();

        // 각도 계산 (이전 코드 유지)
        if (left_angle < 90) {
          left_angle = 0;
        }
        else if (left_angle >= 90 && left_angle < 270) {
          left_angle = left_angle - 90;
        }
        else {
          left_angle = 80;
        }

        if (right_angle < 90) {
          right_angle = 90 - right_angle;
        }
        else if (right_angle >= 90 && right_angle < 180) {
          right_angle = 0;
        }
        else if (right_angle >= 180 && right_angle < 270) {
          right_angle = 180;
        }
        else {
          right_angle = 450 - right_angle;
        }

        // 각도를 서보 모터로 전달
        servo1.write(left_angle);
        servo2.write(abs(180 - right_angle));

        // 디버깅을 위한 출력
        Serial.println("Received: " + input_data);
      }
      // 다음 입력을 위해 초기화
      input_data = "";
    }
    else {
      input_data += incomingByte; // 줄바꿈 문자가 아니라면 문자열에 추가
    }
  }
}
