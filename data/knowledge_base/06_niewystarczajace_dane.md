# Niewystarczające dane

Klasa "niewystarczające dane" jest przypisywana w dwóch przypadkach: gdy
w oknie pomiarowym zebrano zbyt mało pomiarów (poniżej wymaganego
minimum, domyślnie 6), albo gdy zbyt duży odsetek pomiarów PM10/PM2.5 w
oknie jest brakujący (powyżej 30%).

Ta klasa nie mówi nic o faktycznym stanie jakości powietrza - oznacza
jedynie, że dostępnych danych jest za mało, aby wiarygodnie ocenić
sytuację według przyjętej metodyki.

Najczęstsze przyczyny: stacja pomiarowa dopiero rozpoczęła
raportowanie (rozgrzewanie się okna pomiarowego po starcie systemu),
przerwa w łączności z czujnikiem, awaria zasilania stacji lub błąd
transmisji danych.

Zalecenie: brak podstaw do formułowania zaleceń zdrowotnych na podstawie
tego okna - należy poczekać na kolejne pomiary lub sprawdzić stan
techniczny/łączność stacji pomiarowej.
