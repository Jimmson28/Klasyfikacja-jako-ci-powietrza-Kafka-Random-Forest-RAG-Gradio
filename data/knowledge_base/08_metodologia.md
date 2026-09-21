# Metodyka klasyfikacji - podsumowanie

System dzieli strumień pomiarów każdej stacji na okna kroczące
obejmujące ostatnie 12 pomiarów. Dla każdego okna liczone są statystyki
PM10 i PM2.5: średnia, odchylenie standardowe, wartość minimalna i
maksymalna, współczynnik zmienności oraz względna zmiana między
pierwszym a ostatnim pomiarem w oknie.

Klasa okna jest ustalana w oparciu o jednoznaczne, liczbowe progi
(zdefiniowane w dokumencie metodyki projektu), sprawdzane w ustalonej
kolejności: najpierw wystarczalność danych, potem stabilność pomiaru,
potem gwałtowność zmiany (pogorszenie/poprawa), a na końcu poziom
średniego stężenia względem wartości referencyjnych WHO. Ostateczną
klasę publikuje model Random Forest, wytrenowany na przykładach
etykietowanych właśnie tą metodyką - dzięki czemu jego decyzje pozostają
zgodne z przyjętymi progami, a nie z arbitralną oceną modelu językowego.

Model językowy, który generuje wyjaśnienia dla użytkownika, nie ustala
żadnych progów ani nie podejmuje decyzji klasyfikacyjnej - otrzymuje
gotową klasę, policzone statystyki oraz odpowiedni fragment tej bazy
wiedzy i na tej podstawie formułuje zrozumiałe wyjaśnienie w języku
naturalnym.
