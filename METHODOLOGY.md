# Metodyka

Tutaj jest opisane, jak przypisujemy okno pomiarowe do jednej z sześciu klas. Model językowy nie ustala progów, wszystkie są w `common/config.py`.

## Okno

Okno to ostatnie 12 pomiarów jednej stacji. Jeśli jest w nim mniej niż 6 pomiarów, mamy za mało danych.

Dla PM10 i PM2.5 liczymy średnią, odchylenie standardowe, pierwszą i ostatnią wartość, współczynnik zmienności (odchylenie / średnia) oraz zmianę względną ((ostatnia - pierwsza) / pierwsza).

## Progi

| próg | wartość | skąd |
|---|---|---|
| PM10 norma WHO | 45 µg/m3 | wytyczne WHO 2021 |
| PM2.5 norma WHO | 15 µg/m3 | wytyczne WHO 2021 |
| PM10 alarmowe | 150 µg/m3 | ok. 3 razy WHO, przyjęte na potrzeby projektu |
| PM2.5 alarmowe | 50 µg/m3 | ok. 3 razy WHO, przyjęte na potrzeby projektu |
| zmienność | 0.5 | przyjęte na potrzeby projektu |
| gwałtowna zmiana | 50% | przyjęte na potrzeby projektu |
| braki danych | 30% | przyjęte na potrzeby projektu |

## Kolejność reguł

Pierwsza spełniona reguła wygrywa.

1. niewystarczające dane: mniej niż 6 pomiarów albo ponad 30% braków
2. niestabilny pomiar: zmienność PM10 lub PM2.5 większa niż 0.5
3. gwałtowne pogorszenie: wzrost o co najmniej 50% i ostatnia wartość na poziomie alarmowym
4. poprawa: spadek o co najmniej 50% i pierwsza wartość w oknie co najmniej równa normie WHO
5. podwyższone stężenie pyłów: średnia PM10 lub PM2.5 powyżej normy WHO
6. typowy profil pomiarowy: cała reszta

## Random Forest

Dane treningowe robi `ml/generate_training_data.py`: generuje symulowane pomiary i nadaje im etykiety tymi samymi regułami. Na tych danych uczy się Random Forest. Podczas działania systemu klasę wybiera Random Forest, a reguły są liczone obok, żeby sprawdzać, czy się zgadzają (metryka w Grafanie).
