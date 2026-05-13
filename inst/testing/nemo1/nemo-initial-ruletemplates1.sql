--
-- PostgreSQL database dump
--

-- Dumped from database version 12.22 (Debian 12.22-1.pgdg120+1)
-- Dumped by pg_dump version 12.22 (Debian 12.22-1.pgdg120+1)

--
-- Data for Name: mitigations_ruletemplate; Type: TABLE DATA; Schema: public; Owner: nemo
--

COPY public.mitigations_ruletemplate (id, description, description_editable, direction, direction_editable, src_nets, src_nets_editable, dst_nets, dst_nets_editable, protocol, protocol_editable, src_ports, src_ports_editable, dst_ports, dst_ports_editable, action, action_editable, limit_bps, limit_bps_editable) FROM stdin;
1	drop default in	t	in	t		t		t		t		t		f	drop	t	\N	t
2	drop default out	t	out	t		t		t		t		t		t	drop	t	\N	t
\.


--
-- Name: mitigations_ruletemplate_id_seq; Type: SEQUENCE SET; Schema: public; Owner: nemo
--

SELECT pg_catalog.setval('public.mitigations_ruletemplate_id_seq', 2, true);


--
-- PostgreSQL database dump complete
--

