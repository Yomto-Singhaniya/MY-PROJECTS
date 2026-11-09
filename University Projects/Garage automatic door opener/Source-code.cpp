#include <Servo.h>

Servo motor;

int trigPin = 2;
int echoPin = 3;
int distance;
long duration;

void setup() {
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  motor.attach(9);
  motor.write(0);  // Gate closed
}

void loop() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  duration = pulseIn(echoPin, HIGH, 30000);
  distance = (duration == 0) ? 999 : duration * 0.034 / 2;

  if (distance <= 15) {
    motor.write(90);  // Open immediately
    delay(5000);      // Wait 5 seconds
    motor.write(0);   // Close gate
    delay(500);
  }
}