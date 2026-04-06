INSERT INTO camera (id, name, status, location) VALUES (1, '猪舍A - 北区', 'online', '猪舍A') ON DUPLICATE KEY UPDATE name=VALUES(name), status=VALUES(status), location=VALUES(location);
INSERT INTO camera (id, name, status, location) VALUES (2, '猪舍B - 南区', 'online', '猪舍B') ON DUPLICATE KEY UPDATE name=VALUES(name), status=VALUES(status), location=VALUES(location);
INSERT INTO camera (id, name, status, location) VALUES (3, '育肥区 - 01', 'online', '育肥舍') ON DUPLICATE KEY UPDATE name=VALUES(name), status=VALUES(status), location=VALUES(location);
INSERT INTO camera (id, name, status, location) VALUES (4, '监控廊道', 'offline', '办公区') ON DUPLICATE KEY UPDATE name=VALUES(name), status=VALUES(status), location=VALUES(location);

INSERT INTO environment_trend (id, time, area, temperature, humidity) VALUES (1, '0:00', '猪舍A', 37.5, 55.2) ON DUPLICATE KEY UPDATE time=VALUES(time), area=VALUES(area), temperature=VALUES(temperature), humidity=VALUES(humidity);
INSERT INTO environment_trend (id, time, area, temperature, humidity) VALUES (2, '4:00', '猪舍A', 36.8, 60.1) ON DUPLICATE KEY UPDATE time=VALUES(time), area=VALUES(area), temperature=VALUES(temperature), humidity=VALUES(humidity);
INSERT INTO environment_trend (id, time, area, temperature, humidity) VALUES (3, '8:00', '猪舍A', 38.2, 50.5) ON DUPLICATE KEY UPDATE time=VALUES(time), area=VALUES(area), temperature=VALUES(temperature), humidity=VALUES(humidity);
INSERT INTO environment_trend (id, time, area, temperature, humidity) VALUES (4, '0:00', '猪舍B', 36.5, 53.2) ON DUPLICATE KEY UPDATE time=VALUES(time), area=VALUES(area), temperature=VALUES(temperature), humidity=VALUES(humidity);
INSERT INTO environment_trend (id, time, area, temperature, humidity) VALUES (5, '4:00', '猪舍B', 35.8, 58.1) ON DUPLICATE KEY UPDATE time=VALUES(time), area=VALUES(area), temperature=VALUES(temperature), humidity=VALUES(humidity);
INSERT INTO environment_trend (id, time, area, temperature, humidity) VALUES (6, '8:00', '猪舍B', 37.2, 48.5) ON DUPLICATE KEY UPDATE time=VALUES(time), area=VALUES(area), temperature=VALUES(temperature), humidity=VALUES(humidity);

INSERT INTO pig (id, score, issue, body_temp, activity_level, breed) VALUES ('PIG-001', 95, '体温过高', 40.5, 60, '两头乌') ON DUPLICATE KEY UPDATE score=VALUES(score), issue=VALUES(issue), body_temp=VALUES(body_temp), activity_level=VALUES(activity_level);
INSERT INTO pig (id, score, issue, body_temp, activity_level, breed) VALUES ('PIG-002', 10, NULL, 38.5, 90, '杜洛克') ON DUPLICATE KEY UPDATE score=VALUES(score), issue=VALUES(issue), body_temp=VALUES(body_temp), activity_level=VALUES(activity_level);
INSERT INTO pig (id, score, issue, body_temp, activity_level, breed) VALUES ('PIG-003', 80, '跛行', 38.6, 40, '长白') ON DUPLICATE KEY UPDATE score=VALUES(score), issue=VALUES(issue), body_temp=VALUES(body_temp), activity_level=VALUES(activity_level);

INSERT INTO alert (id, pig_id, area, type, risk, timestamp) VALUES (1, 'PIG-001', '猪舍A', '发热', 'High', '2023-10-27 10:00:00') ON DUPLICATE KEY UPDATE pig_id=VALUES(pig_id), area=VALUES(area), type=VALUES(type), risk=VALUES(risk), timestamp=VALUES(timestamp);
INSERT INTO alert (id, pig_id, area, type, risk, timestamp) VALUES (2, 'PIG-003', '猪舍A', '受伤', 'Medium', '2023-10-27 11:30:00') ON DUPLICATE KEY UPDATE pig_id=VALUES(pig_id), area=VALUES(area), type=VALUES(type), risk=VALUES(risk), timestamp=VALUES(timestamp);

INSERT INTO sys_user (username, password, nickname, status) VALUES ('admin', '$2a$10$eum/w4tVTlGovPGv8aL9ge6uhZWJo/MqcYcAYZTugjU17Rgym0Y8u', '管理员', '0') ON DUPLICATE KEY UPDATE password=VALUES(password), nickname=VALUES(nickname), status=VALUES(status);
INSERT INTO sys_user (username, password, nickname, status) VALUES ('user', '$2a$10$eum/w4tVTlGovPGv8aL9ge6uhZWJo/MqcYcAYZTugjU17Rgym0Y8u', '普通用户', '0') ON DUPLICATE KEY UPDATE password=VALUES(password), nickname=VALUES(nickname), status=VALUES(status);
