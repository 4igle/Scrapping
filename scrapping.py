import requests
import re
from alive_progress import alive_bar


def get_page(url):
    """
    Fonction qui récupère le code html d'une page web
    """
    try:
        page = requests.get(url)
        return page.text
    except:
        return None


def get_emails(page):
    """
    Fonction qui extrait les e-mails d'un texte
    """
    emails = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", page)
    return unique(emails)


def get_phones(page):
    """
    Fonction qui extrait les numéros de tél d'un texte
    Ne prend que les (vrais) numéros de téléphone, par exemple si dans le html on a :
    f.header.value = 507658984511, il ne faut pas extraire le numéro 0765898451

    Pour cela, on met un \b (délimiteur de mot) à la fin de l'expression régulière,
    et [>= ] au début, car avant le numéro, il y aura soit un espace, soit la fermeture d'une
    balise html, soit un égal, on évite que le numéro soit juste des chiffres parmi d'autres.
    """

    phones_fr = re.findall(r"[>= ](?:(?:\+|00)33|0)\s*[\d](?:[\s.-]*\d{2}){4}\b", page)
    phones_us = re.findall(r"[>= ]\+?\d{0,2}[ -]\(?\d{3}\)?[ -]\d{3}[ -]\d{4}\b", page)

    # On enlève le premier caractère de chaque numéro
    for i in range(len(phones_fr)):
        phones_fr[i] = extraire(phones_fr[i])
        if not check_phone_validity(phones_fr[i]): #erreur ici argument
            phones_fr[i] = ""
    phones_fr = del_empty(phones_fr)

    for i in range(len(phones_us)):
        phones_us[i] = extraire(phones_us[i])

    phones = phones_fr + phones_us

    return unique(phones)


def get_links(page):
    """
    Fonction qui extrait les liens d'un texte

    Étant donné que les liens prennent plein de formes différentes et ne commencent pas tous
    par http (peuvent être relatifs), on se contente de récupérer toutes les valeurs des attributs href
    """
    links = re.findall(r'href="([^"]+)"', page)
    return unique(links)


def check_phone_validity(tel):
    """
    Fonction qui vérifie si une chaîne qui est a priori numéro de téléphone est valide
    """
    separateur = None
    for i in range(len(tel)):

        # Vérifie que le séparateur est bon et reste le même
        if not tel[i].isdigit() and tel[i] != "+":

            # Pas d'autre non-chiffre que + au début
            if i == 0:
                return False

            # Si le séparateur n'a pas encore été défini
            elif not separateur:
                # Que ces séparateurs autorisés
                if tel[i] not in [".", "-", " "]:
                    return False
                separateur = tel[i]

            # Si le séparateur est différent
            elif separateur != tel[i]:
                return False

            # Pas deux séparateurs successifs
            elif tel[i] == tel[i-1]:
                return False

    return True


def extraire(string):
    """
    Fontion qui enlève le premier caractère d'une chaine
    """
    return string[1:]


def full_link(url_base, link):
    """
    Fonction qui permet de transformer un lien relatif en lien complet

    Exemple :
        si on a trouvé https://facebook.com/ sur le site https://google.com/,
        on renvoit https://facebook.com/

        si on a trouvé /contact/fr/ sur le site https://google.com/,
        on renvoit https://google.com/contact/fr
    """
    if link == "":
        return ""

    if link[0] == "/":
        return f"{url_base}{link[1:]}"
    elif link[0:4] == "http":
        return link
    else:
        return ""


def del_empty(liste):
    """
    Fonction qui supprime les éléments vides d'une liste
    """
    return [e for e in liste if e]


def unique(liste):
    """
    Fonction qui supprime les doublons d'une liste
    """
    return list(set(liste))


def recherche(url, all_emails, all_phones, links_already_visited, occurences, profondeur_max, profondeur=1, enregistrer=False):
    """
    Fonction récursive qui recherche tous les liens, e-mail, téléphones
    d'une page web et des sous-pages web de profondeur inférieure ou égale
    à la valeur de profondeur
    """

    if profondeur > 0:

        # print(f"Recherche de {url}")

        links_already_visited.append(url)

        page = get_page(url)
        if page:
            emails_current_page = get_emails(page)
            phones_current_page = get_phones(page)
            links_current_page = get_links(page)

            # Transformation en lien absolu et suppression des éléments n'étant pas des liens
            for i in range(len(links_current_page)):
                links_current_page[i] = full_link(url, links_current_page[i])
            links_current_page = del_empty(links_current_page)

            # print(emails_current_page)
            # print(phones_current_page)
            # print(links_current_page)
            if profondeur == profondeur_max:
                with alive_bar(len(links_current_page)) as bar:
                    for link in links_current_page:
                        bar()
                        if link not in links_already_visited:
                            recherche(link, all_emails, all_phones, links_already_visited, occurences, profondeur_max, profondeur-1, enregistrer)

            else:
                for link in links_current_page:
                    if link not in links_already_visited:
                        recherche(link, all_emails, all_phones, links_already_visited, occurences, profondeur_max, profondeur-1, enregistrer)

            for email in emails_current_page:
                if email not in all_emails:
                    all_emails.append(email)
                    occurences[email] = [1, [domaine(url)]]
                else:
                    occurences[email][0] += 1
                    if domaine(url) not in occurences[email][1]:
                        occurences[email][1].append(domaine(url))

            for phone in phones_current_page:
                if not check_phone(deletespaces(phone), all_phones):
                    all_phones.append(phone)
                    occurences[deletespaces(phone)] = [1, [domaine(url)]]
                else:
                    occurences[deletespaces(phone)][0] += 1
                    if domaine(url) not in occurences[deletespaces(phone)][1]:
                        occurences[deletespaces(phone)][1].append(domaine(url))

        if enregistrer and profondeur == profondeur_max:
            with open("emails.txt", "w") as f:
                for email in all_emails:
                    f.write(email + "\n")
            with open("phones.txt", "w") as f:
                for phone in all_phones:
                    f.write(phone + "\n")
            with open("links.txt", "w") as f:
                for link in sorted(links_already_visited):
                    f.write(link + "\n")


def enum_list_string(liste):
    """
    Fonction qui permet d'afficher les éléments d'une liste séparés d'une virgule
    """
    return ", ".join(liste)


def deletespaces(string):
    """
    Fonction qui supprime les espaces d'une chaine
    """
    return string.replace(" ", "")


def check_phone(phone, all_phones):
    """
    Fonction qui vérifie si un numéro de téléphone sans espace
    existe déjà dans la liste avec des espaces
    """
    for p in all_phones:
        if deletespaces(p) == phone:
            return True
    return False


def domaine(url):
    """
    Fonction qui renvoie le domaine d'une url
    """
    return url.split("/")[2]


def main():
    """
    Fonction principale qui permet d'extraire les informations
    """
    url = input("Entrez l'url de la page web : ")
    p = int(input("Entrez la profondeur de recherche : "))
    enr = input("Voulez-vous enregistrer les résultats ? (y/n) : ")
    if enr == "y":
        enr = True
    else:
        enr = False

    all_emails = []
    all_phones = []
    links_already_visited = []
    occurences = dict()
    recherche(url, all_emails, all_phones, links_already_visited, occurences, p, profondeur=p, enregistrer=enr)

    print("\nE-mails trouvés :")
    for email in all_emails:
        print(f"  - {email} : {occurences[email][0]} occurence(s), trouvé sur {enum_list_string(occurences[email][1])}")
    if len(all_emails) == 0:
        print("Aucun e-mail trouvé")

    print("\nTéléphones trouvés :")
    for phone in all_phones:
        print(f"  - {phone} : {occurences[deletespaces(phone)][0]} occurence(s), trouvé sur {enum_list_string(occurences[deletespaces(phone)][1])}")
    if len(all_phones) == 0:
        print("Aucun téléphone trouvé")

    print(f"\n{len(links_already_visited)} liens trouvés")
    afficher_liens = input("\nVoulez-vous les afficher ? (y/n) : ")
    if afficher_liens == "y":
        print("\nLiens visités :")
        for link in sorted(links_already_visited):
            print(f"  - {link}")


if __name__ == "__main__":
    main()
