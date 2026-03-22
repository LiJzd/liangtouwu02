MERGE INTO camera (id, name, status, location) KEY(id) VALUES (1, '猪舍A - 北区', 'online', '猪舍A');
MERGE INTO camera (id, name, status, location) KEY(id) VALUES (2, '猪舍B - 南区', 'offline', '猪舍B');

MERGE INTO environment_trend (id, time, area, temperature, humidity) KEY(id) VALUES (1, '0:00', '猪舍A', 37.5, 55.2);
MERGE INTO environment_trend (id, time, area, temperature, humidity) KEY(id) VALUES (2, '4:00', '猪舍A', 36.8, 60.1);
MERGE INTO environment_trend (id, time, area, temperature, humidity) KEY(id) VALUES (3, '8:00', '猪舍A', 38.2, 50.5);
MERGE INTO environment_trend (id, time, area, temperature, humidity) KEY(id) VALUES (4, '0:00', '猪舍B', 36.5, 53.2);
MERGE INTO environment_trend (id, time, area, temperature, humidity) KEY(id) VALUES (5, '4:00', '猪舍B', 35.8, 58.1);
MERGE INTO environment_trend (id, time, area, temperature, humidity) KEY(id) VALUES (6, '8:00', '猪舍B', 37.2, 48.5);

MERGE INTO pig (id, score, issue, body_temp, activity_level) KEY(id) VALUES ('PIG-001', 95, '体温过高', 40.5, 60);
MERGE INTO pig (id, score, issue, body_temp, activity_level) KEY(id) VALUES ('PIG-002', 10, NULL, 38.5, 90);
MERGE INTO pig (id, score, issue, body_temp, activity_level) KEY(id) VALUES ('PIG-003', 80, '跛行', 38.6, 40);

MERGE INTO alert (id, pig_id, area, type, risk, timestamp) KEY(id) VALUES (1, 'PIG-001', '猪舍A', '发热', 'High', '2023-10-27 10:00:00');
MERGE INTO alert (id, pig_id, area, type, risk, timestamp) KEY(id) VALUES (2, 'PIG-003', '猪舍A', '受伤', 'Medium', '2023-10-27 11:30:00');

MERGE INTO sys_user (username, password, role) KEY(username) VALUES ('admin', '$2a$10$eum/w4tVTlGovPGv8aL9ge6uhZWJo/MqcYcAYZTugjU17Rgym0Y8u', 'admin');
MERGE INTO sys_user (username, password, role) KEY(username) VALUES ('user', '$2a$10$eum/w4tVTlGovPGv8aL9ge6uhZWJo/MqcYcAYZTugjU17Rgym0Y8u', 'user');
