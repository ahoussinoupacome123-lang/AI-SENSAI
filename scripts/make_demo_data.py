"""Build stand-in demo data: a 24-page text PDF about networks with facts planted on known pages.

    python scripts/make_demo_data.py [output_folder]        (default: data/synthetic)

Writes demo.pdf, questions.txt (8 covered questions and 1 the PDF does not cover) and
expected_answers.md in the format read by scripts/e2e_check.py. Use it when the real
demo PDF is not available yet; the real demo data should replace it.
"""
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from pdf_factory import make_text_pdf  # noqa: E402

TOPICS = ["Introduction to networks","Network topologies","The OSI model","The TCP/IP model","IP addressing",
 "Routing basics","The transport layer","Ports and sockets","The domain name system","Email protocols","The web and HTTP",
 "Web security","HTTPS and TLS","Network address translation","Subnetting","Switches and VLANs","Wireless networks",
 "Wi-Fi standards","Network monitoring","Firewalls","Virtual private networks","Cloud networking","Troubleshooting","Summary"]
FACTS = {
 3:"The OSI model has seven layers: physical, data link, network, transport, session, presentation and application.",
 5:"IPv4 addresses are 32 bits long, which allows about 4.3 billion distinct addresses.",
 7:"TCP uses a three-way handshake made of SYN, SYN-ACK and ACK segments to open a connection.",
 9:"DNS translates domain names into IP addresses and listens on port 53.",
 11:"HTTP status code 404 means that the requested resource was not found on the server.",
 13:"The default port for HTTPS is 443, and TLS encrypts the traffic between the browser and the server.",
 15:"A subnet mask of 255.255.255.0 gives 254 usable host addresses in the network.",
 18:"Wi-Fi 6 is also known as IEEE 802.11ax and reaches a theoretical maximum of 9.6 Gbit/s."}
FILLER = ["This chapter explains the main ideas step by step and gives short examples that a beginner can follow.",
 "Engineers use these concepts every day when they design, build and maintain networks of every size.",
 "A good way to learn is to draw the network on paper and follow a message from the sender to the receiver.",
 "Many problems in practice come from a small configuration mistake, so careful checking is an important habit.",
 "Standards bodies publish documents so that equipment from different makers can work together without surprises.",
 "Performance depends on bandwidth, delay and the amount of traffic that shares the same links.",
 "Security must be considered from the start, because adding it later is usually harder and more expensive.",
 "Students often confuse similar terms, so it helps to write a one line definition for each new word."]
pages = []
for n, topic in enumerate(TOPICS, start=1):
    parts = [f"Chapter {n}: {topic}.", FILLER[n % 8], FILLER[(n + 3) % 8]]
    if n in FACTS: parts.insert(2, FACTS[n])
    parts += [FILLER[(n + 5) % 8], f"Key idea of {topic.lower()}: keep the design simple and test every step."]
    pages.append("\n".join(textwrap.fill(p, 88) for p in parts))
out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "synthetic"
out.mkdir(parents=True, exist_ok=True)
make_text_pdf(out / "demo.pdf", pages)
questions = ["How many layers does the OSI model have and what are they?","How many bits long is an IPv4 address?",
 "What are the three steps of the TCP handshake?","Which port does DNS use?","What does HTTP status code 404 mean?",
 "What is the default port for HTTPS?","How many usable host addresses does a 255.255.255.0 subnet mask give?",
 "What is the theoretical maximum speed of Wi-Fi 6?","Who founded the company Cisco?"]
(out / "questions.txt").write_text("\n".join(questions) + "\n")
(out / "expected_answers.md").write_text("# Expected answers\n\n" + "\n".join([
 "1 | page 3 | The OSI model has seven layers","2 | page 5 | IPv4 addresses are 32 bits long","3 | page 7 | three-way handshake made of SYN, SYN-ACK and ACK",
 "4 | page 9 | listens on port 53","5 | page 11 | HTTP status code 404 means","6 | page 13 | The default port for HTTPS is 443",
 "7 | page 15 | gives 254 usable host addresses","8 | page 18 | 9.6 Gbit/s","9 | none |"]) + "\n")
print(f"wrote {out}/demo.pdf ({len(pages)} pages), questions.txt, expected_answers.md")
