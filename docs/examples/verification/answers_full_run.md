# Answers

<!-- sensai:section 1 -->
## Q1. How many bits long is an IPv6 address?

**Answer:** 128 bits

**Page:** 13

> An IPv6 address is 128 bits long, which gives about 3.4 times ten to the power 38 addresses, an amount large enough to give a unique address to every device for the foreseeable future.

**Quote check:** supported
**Judge:** faithful - The answer states that an IPv6 address is 128 bits long, and Passage 1 explicitly mentions that 'An IPv6 address is 128 bits long'.
<!-- /sensai:section 1 -->

<!-- sensai:section 2 -->
## Q2. What are the four steps of the DHCP process?

**Answer:** 

**Page:** -

_(no quote)_

**Quote check:** not supported
**Judge:** faithful - The answer states the four steps of DHCP as Discover, Offer, Request, and Acknowledge, which is directly stated in Passage 1 as DORA (Discover, Offer, Request, Acknowledge).
**Review needed:** the quote check and the judge disagree.
<!-- /sensai:section 2 -->

<!-- sensai:section 3 -->
## Q3. How many usable host addresses does a /26 subnet give?

**Answer:** 62

**Page:** 12

> A /26 network has 6 host bits, so it gives 64 addresses in total and 62 usable host addresses.

**Quote check:** supported
**Judge:** faithful - The answer states 62 usable host addresses for a /26 subnet, and both Passage 1 and Passage 2 explicitly mention that a /26 network gives 64 addresses in total and 62 usable host addresses.
<!-- /sensai:section 3 -->

<!-- sensai:section 4 -->
## Q4. Which Wi-Fi channels in the 2.4 GHz band do not overlap?

**Answer:** The three channels 1, 6 and 11

**Page:** 22

> The three channels 1, 6 and 11 do not overlap, so access points close to each other should use them to avoid interference.

**Quote check:** supported
**Judge:** faithful - The passages explicitly state that 'The three channels 1, 6 and 11 do not overlap, so access points close to each other should use them to avoid interference.'
<!-- /sensai:section 4 -->

<!-- sensai:section 5 -->
## Q5. What is the maximum payload size of an Ethernet frame?

**Answer:** 1500 bytes

**Page:** 8

> The maximum payload of an Ethernet frame is 1500 bytes, a limit known as the maximum transmission unit, or MTU.

**Quote check:** supported
**Judge:** faithful - The answer states '1500 bytes' which is explicitly mentioned in both Passage 1 and Passage 2 as the maximum payload of an Ethernet frame, known as the MTU.
<!-- /sensai:section 5 -->

<!-- sensai:section 6 -->
## Q6. Which port does SSH use?

**Answer:** The document does not cover this.

**Page:** -

_(no quote)_

**Quote check:** not supported
**Judge:** unfaithful - The passages explicitly state that SSH uses port 22 in Passage 1.
**Review needed:** the model says the document does not cover this, but the judge says the passages answer it.
<!-- /sensai:section 6 -->

<!-- sensai:section 7 -->
## Q7. What does the TTL field do in an IP packet?

**Answer:** The TTL field limits the lifetime of a packet: each router that forwards the packet decreases the value by one, and when it reaches zero the router discards the packet and sends an error message back to the sender. This prevents packets from circling forever if a routing loop occurs.

**Page:** 14

> The TTL field limits the lifetime of a packet: each router that forwards the packet decreases the value by one, and when it reaches zero the router discards the packet and sends an error message back to the sender. This prevents packets from circling forever if a routing loop occurs.

**Quote check:** supported
**Judge:** faithful - The answer directly quotes the explanation from Passage 1 about the TTL field's function, including how it limits packet lifetime, routers decrementing the value, discarding at zero, and preventing routing loops.
<!-- /sensai:section 7 -->

<!-- sensai:section 8 -->
## Q8. How long is an 802.1Q VLAN tag?

**Answer:** 4 bytes long

**Page:** 10

> The 802.1Q tag is 4 bytes long, and 12 of its bits hold the VLAN identifier.

**Quote check:** supported
**Judge:** faithful - The passages state that the 802.1Q tag is 4 bytes long in both Passage 1 and Passage 2.
<!-- /sensai:section 8 -->

<!-- sensai:section 9 -->
## Q9. Who invented the World Wide Web?

**Answer:** The document does not cover this.

**Page:** -

_(no quote)_

**Quote check:** not supported
**Judge:** faithful - The answer states that the document does not cover who invented the World Wide Web, but the passages discuss network types, internet infrastructure, and DNS without mentioning the inventor of the World Wide Web.
<!-- /sensai:section 9 -->

