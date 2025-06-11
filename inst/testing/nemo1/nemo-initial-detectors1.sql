--
-- PostgreSQL database dump
--

-- Dumped from database version 12.22 (Debian 12.22-1.pgdg120+1)
-- Dumped by pg_dump version 12.22 (Debian 12.22-1.pgdg120+1)

--
-- Data for Name: detector; Type: TABLE DATA; Schema: public; Owner: nemo
--

COPY public.detector (id, name, detector_type, num_threads, autostart, visibility, objectfilter) FROM stdin;
1	th1	threshold	1	t	name	oid == "net_2"
\.


--
-- Data for Name: detector_param; Type: TABLE DATA; Schema: public; Owner: nemo
--

COPY public.detector_param (id, object_id, object_type, name, val, detector_id) FROM stdin;
56	\N	\N	field_name	numbytes	1
57	\N	\N	info_above	10000	1
58	\N	\N	warn_above	20000	1
59	\N	\N	critical_above	50000	1
\.


--
-- Data for Name: tag; Type: TABLE DATA; Schema: public; Owner: nemo
--

COPY public.tag (id, name, scope, expired) FROM stdin;
1	attacker	object	f
2	victim	object	f
\.


--
-- Data for Name: tagged_item; Type: TABLE DATA; Schema: public; Owner: nemo
--

COPY public.tagged_item (id, object_id, content_type_id, tag_id, automatic) FROM stdin;
1	1	15	1	f
2	2	15	2	f
\.


--
-- Data for Name: trigger; Type: TABLE DATA; Schema: public; Owner: nemo
--

COPY public.trigger (id, name, description, trigger_type, autostart, email, description_template, subject_template, body_template, short_open_template, long_open_template, short_upgrade_template, long_upgrade_template, short_close_template, long_close_template, default_filter, do_not_send_mails, mail_analysis_severity, watsond_body_template, watsond_subject_template) FROM stdin;
2	evw2		time_window	t	\N											f	100	\N	\N
1	evw		time_window	t	\N											f	100	\N	\N
\.


--
-- Data for Name: timewindowtrigger; Type: TABLE DATA; Schema: public; Owner: nemo
--

COPY public.timewindowtrigger (triggerconfig_ptr_id, per_object, per_event_type, per_detector, open_conditions, upgrade_conditions1, upgrade_conditions2, close_conditions) FROM stdin;
2	f	t	f	{"severity":"2","op":"all","conds":[{"type":"timewindow","comp":"gt","count":"0","minutes":"5","filter":[{"type":"detector_id","comp":"eq","val":"1"},{"type":"severity","comp":"eq","val":"2"}],"filter_op":"all"}]}	{"severity":"0","op":"all","conds":[]}	{"severity":"0","op":"all","conds":[]}	{"op":"all","conds":[{"type":"timewindow","comp":"lt","count":"1","minutes":"5","filter":[{"type":"detector_id","comp":"eq","val":"1"},{"type":"severity","comp":"eq","val":"2"}],"filter_op":"all"}]}
1	f	f	t	{"severity":"0","op":"all","conds":[{"type":"timewindow","comp":"gt","count":"0","minutes":"5","filter":[{"type":"detector_id","comp":"eq","val":"1"}],"filter_op":"all"}]}	{"severity":"0","op":"all","conds":[]}	{"severity":"0","op":"all","conds":[]}	{"op":"all","conds":[{"type":"timewindow","comp":"lt","count":"1","minutes":"5","filter":[{"type":"detector_id","comp":"eq","val":"1"}],"filter_op":"all"}]}
\.


--
-- Name: detector_id_seq; Type: SEQUENCE SET; Schema: public; Owner: nemo
--

SELECT pg_catalog.setval('public.detector_id_seq', 1, false);


--
-- Name: detector_param_id_seq; Type: SEQUENCE SET; Schema: public; Owner: nemo
--

SELECT pg_catalog.setval('public.detector_param_id_seq', 1, false);


--
-- Name: tag_id_seq; Type: SEQUENCE SET; Schema: public; Owner: nemo
--

SELECT pg_catalog.setval('public.tag_id_seq', 2, true);


--
-- Name: tagged_item_id_seq; Type: SEQUENCE SET; Schema: public; Owner: nemo
--

SELECT pg_catalog.setval('public.tagged_item_id_seq', 2, true);


--
-- Name: trigger_id_seq; Type: SEQUENCE SET; Schema: public; Owner: nemo
--

SELECT pg_catalog.setval('public.trigger_id_seq', 2, true);


--
-- PostgreSQL database dump complete
--

