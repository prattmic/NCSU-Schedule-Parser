#!/usr/bin/env python

from bs4 import BeautifulSoup

soup = BeautifulSoup(open("schedule.html"))

classes = []

for data in soup.find_all("tbody")[1].contents:
    td = data.find_all("td")
    if not td:
        continue

    cls = {}
    cls["name"]         = td[0].a.contents[0]
    cls["section"]      = td[1].contents[0]
    cls["description"]  = td[2].contents[0]
    cls["credits"]      = td[3].contents[0]
    cls["days"]         = td[4].contents[0]
    cls["time"]         = td[5].contents[0]
    cls["room"]         = td[6].contents[0]

    classes.append(cls)

for cls in classes:
    print cls
