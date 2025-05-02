# Yhteisöpalvelu

## Keskeiset toiminnot
- Käyttäjä voi rekisteröityä ja kirjautua palveluun
- Käyttäjä voi lisätä, muokata ja poistaa postauksia
- Käyttäjä voi luokitella postauksensa kahteen eri kategoriaan
- Käyttäjä voi kommentoida muiden käyttäjien postauksia sekä muokata ja poistaa kommentteja
- Käyttäjä voi etsiä hakusanalla postauksia ja kommentteja
- Käyttäjäsivuilta näkee tilastoja käyttäjästä ja voi poistaa käyttäjän
- "admin"-nimisestä käyttäjästä tehdään automaattisesti pääkäyttäjä
- Pääkäyttäjä voi muokata ja poistaa mitä tahansa

## Sovelluksen käyttö
Asenna `flask`-kirjasto

```console
$ pip install flask
```

Luo tietokannan taulut ja config-tiedosto

```console
$ python init.py
```

Käynnistä sovellus

```console
$ python app.py
```

### Suuri tietomäärä
Sovellusta on testattu suurella tietomäärällä (1000 käyttäjää, 100 000 postausta ja 1 000 000 kommenttia).
Tällä tietomäärällä sovellus toimii normaalisti ja kaikki sivut latautuvat alle sekunnissa.
