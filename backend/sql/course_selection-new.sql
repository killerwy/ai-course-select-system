/*
 Navicat Premium Dump SQL
 Source Server         : 111
 Source Server Type    : MySQL
 Source Server Version : 80041 (8.0.41)
 Source Host           : localhost:3306
 Source Schema         : course_selection
 Target Server Type    : MySQL
 Target Server Version : 80041 (8.0.41)
 File Encoding         : 65001
 Date: 17/07/2026 04:16:35
 修改说明：
 1. 添加了 CREATE DATABASE IF NOT EXISTS 语句，自动创建数据库
 2. 添加了 USE 语句自动切换到目标数据库
 3. 保留了 FOREIGN_KEY_CHECKS = 0 以避免外键约束问题
*/
-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `course_selection` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 切换到目标数据库
USE `course_selection`;
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
-- ----------------------------
-- Table structure for audit_logs
-- ----------------------------
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `actor_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `subject_student_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `actor_role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `resource_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `resource_id` varchar(72) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `before_json` json NULL,
  `after_json` json NULL,
  `reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `run_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `request_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `ix_audit_logs_student_created`(`subject_student_id` ASC, `created_at` ASC) USING BTREE,
  INDEX `ix_audit_logs_resource_created`(`resource_type` ASC, `resource_id` ASC, `created_at` ASC) USING BTREE,
  INDEX `ix_audit_logs_run_created`(`run_id` ASC, `created_at` ASC) USING BTREE,
  INDEX `fk_audit_logs_actor`(`actor_id` ASC) USING BTREE,
  CONSTRAINT `fk_audit_logs_actor` FOREIGN KEY (`actor_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_audit_logs_run` FOREIGN KEY (`run_id`) REFERENCES `recalculation_runs` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_audit_logs_student` FOREIGN KEY (`subject_student_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of audit_logs
-- ----------------------------
INSERT INTO `audit_logs` VALUES ('audit-001', 'student-001', 'student-001', 'STUDENT', 'ENROLLMENT_CREATED', 'enrollment', 'enrollment-001', NULL, '{\"status\": \"ENROLLED\", \"course_id\": \"course-101\"}', 'seed data', NULL, 'seed-audit-001', '2026-07-16 18:14:54.712786');
INSERT INTO `audit_logs` VALUES ('audit-0093a9bf4b9c', 'academic-001', NULL, 'ACADEMIC', 'COURSE_OPERATION_SUBMITTED', 'course_operation', 'f85c0a7a-91e2-4958-826c-ab64dc520c8c', '{}', '{\"id\": \"f85c0a7a-91e2-4958-826c-ab64dc520c8c\", \"reason\": null, \"status\": \"PENDING\", \"comment\": null, \"payload\": {\"code\": \"66666\", \"name\": \"666666666\", \"credits\": 3, \"capacity\": 30, \"schedules\": [{\"room\": \"待定\", \"weekday\": 3, \"end_minute\": 840, \"start_minute\": 705}], \"teacher_name\": \"66\", \"prerequisites\": []}, \"course_id\": null, \"operation\": \"CREATE\", \"created_at\": \"2026-07-16T19:09:52.625233+00:00\", \"updated_at\": \"2026-07-16T19:09:52.625233+00:00\", \"reviewer_id\": null, \"requester_id\": \"academic-001\", \"idempotency_key\": \"create-course-66666-mrnvvhpj-4b77f36e\"}', 'course operation submitted', NULL, 'req-966db257a70f', '2026-07-16 19:09:52.625233');
INSERT INTO `audit_logs` VALUES ('audit-28eaa88cf773', 'student-001', 'student-001', 'STUDENT', 'RECOMMENDATION_CREATED', 'recommendation_session', '48dc0e35-1eed-4ebf-9b9c-2ca5ac4f2862', '{}', '{}', NULL, NULL, 'recommendation:48dc0e35-1eed-4ebf-9b9c-2ca5ac4f2862', '2026-07-16 19:37:15.048213');
INSERT INTO `audit_logs` VALUES ('audit-2cc5daf08328', 'academic-001', NULL, 'ACADEMIC', 'COURSE_OPERATION_SUBMITTED', 'course_operation', '6b7ef958-f75e-47d5-926b-47f1ee27819b', '{}', '{\"id\": \"6b7ef958-f75e-47d5-926b-47f1ee27819b\", \"reason\": null, \"status\": \"PENDING\", \"comment\": null, \"payload\": {\"code\": \"12212\", \"name\": \"2121\", \"credits\": 3, \"capacity\": 30, \"schedules\": [{\"room\": \"待定\", \"weekday\": 1, \"end_minute\": 570, \"start_minute\": 480}], \"teacher_name\": \"1212\", \"prerequisites\": []}, \"course_id\": null, \"operation\": \"CREATE\", \"created_at\": \"2026-07-16T18:44:06.293019+00:00\", \"updated_at\": \"2026-07-16T18:44:06.293019+00:00\", \"reviewer_id\": null, \"requester_id\": \"academic-001\", \"idempotency_key\": \"create-course-12212-mrnuycjp-7ee63495\"}', 'course operation submitted', NULL, 'req-6e9f9c56dc25', '2026-07-16 18:44:06.294027');
INSERT INTO `audit_logs` VALUES ('audit-2f51b326a146', 'student-001', 'student-001', 'STUDENT', 'ENROLLMENT_DROPPED', 'enrollment', 'enrollment-001', '{\"status\": \"ENROLLED\", \"course_id\": \"course-101\"}', '{\"status\": \"DROPPED\", \"course_id\": \"course-101\"}', NULL, NULL, 'student:student-001:course-101', '2026-07-16 18:48:00.328647');
INSERT INTO `audit_logs` VALUES ('audit-300f67b130cc', 'student-001', 'student-001', 'STUDENT', 'RECOMMENDATION_CREATED', 'recommendation_session', '69343473-dcd3-40bc-b675-c2557455eb6e', '{}', '{}', NULL, NULL, 'recommendation:69343473-dcd3-40bc-b675-c2557455eb6e', '2026-07-16 19:38:12.998498');
INSERT INTO `audit_logs` VALUES ('audit-33338d119f50', 'student-001', 'student-001', 'STUDENT', 'RECOMMENDATION_CREATED', 'recommendation_session', '8a293702-bf1c-45a1-b8cb-4ea6342a3bcf', '{}', '{}', NULL, NULL, 'recommendation:8a293702-bf1c-45a1-b8cb-4ea6342a3bcf', '2026-07-16 19:36:40.313651');
INSERT INTO `audit_logs` VALUES ('audit-52248a04266e', 'academic-001', NULL, 'ACADEMIC', 'COURSE_OPERATION_SUBMITTED', 'course_operation', 'c3dae33c-2c61-4195-aae4-624106e55c68', '{}', '{\"id\": \"c3dae33c-2c61-4195-aae4-624106e55c68\", \"reason\": null, \"status\": \"PENDING\", \"comment\": null, \"payload\": {\"code\": \"22221111\", \"name\": \"11111\", \"credits\": 3, \"capacity\": 30, \"schedules\": [{\"room\": \"待定\", \"weekday\": 1, \"end_minute\": 570, \"start_minute\": 480}], \"teacher_name\": \"1111\", \"prerequisites\": []}, \"course_id\": null, \"operation\": \"CREATE\", \"created_at\": \"2026-07-16T18:57:41.643749+00:00\", \"updated_at\": \"2026-07-16T18:57:41.643749+00:00\", \"reviewer_id\": null, \"requester_id\": \"academic-001\", \"idempotency_key\": \"create-course-22221111-mrnvftoi-54f15b68\"}', 'course operation submitted', NULL, 'req-b375e45043b7', '2026-07-16 18:57:41.644750');
INSERT INTO `audit_logs` VALUES ('audit-6799dc9478f4', 'student-001', 'student-001', 'STUDENT', 'ENROLLMENT_CREATED', 'enrollment', 'enrollment-001', '{}', '{\"status\": \"ENROLLED\", \"course_id\": \"course-101\"}', NULL, NULL, 'student:student-001:course-101', '2026-07-16 18:48:07.512072');
INSERT INTO `audit_logs` VALUES ('audit-68f4a88188cd', 'academic-001', NULL, 'ACADEMIC', 'COURSE_OPERATION_SUBMITTED', 'course_operation', '580113b9-8ab5-47ca-9c60-35de63ea2acf', '{}', '{\"id\": \"580113b9-8ab5-47ca-9c60-35de63ea2acf\", \"reason\": null, \"status\": \"PENDING\", \"comment\": null, \"payload\": {\"code\": \"99\", \"name\": \"操作系统\", \"credits\": 3, \"capacity\": 30, \"schedules\": [{\"room\": \"待定\", \"weekday\": 1, \"end_minute\": 570, \"start_minute\": 480}], \"teacher_name\": \"1313\", \"prerequisites\": [\"CS101\"]}, \"course_id\": null, \"operation\": \"CREATE\", \"created_at\": \"2026-07-16T19:02:44.291169+00:00\", \"updated_at\": \"2026-07-16T19:02:44.291169+00:00\", \"reviewer_id\": null, \"requester_id\": \"academic-001\", \"idempotency_key\": \"create-course-99-mrnvmayv-c6bb2b38\"}', 'course operation submitted', NULL, 'req-584e1a870864', '2026-07-16 19:02:44.292171');
INSERT INTO `audit_logs` VALUES ('audit-698fab59e980', 'student-001', 'student-001', 'STUDENT', 'RECOMMENDATION_CREATED', 'recommendation_session', '2104703e-da0a-4c95-be47-25f176cb89f9', '{}', '{}', NULL, NULL, 'recommendation:2104703e-da0a-4c95-be47-25f176cb89f9', '2026-07-16 18:59:11.820436');
INSERT INTO `audit_logs` VALUES ('audit-765bca831df9', 'student-001', 'student-001', 'STUDENT', 'ENROLLMENT_CREATED', 'enrollment', 'ab287e0a-6a36-40e1-8974-56d1edb431cc', '{}', '{\"status\": \"ENROLLED\", \"course_id\": \"course-301\"}', NULL, NULL, 'student:student-001:course-301', '2026-07-16 19:00:02.010999');
INSERT INTO `audit_logs` VALUES ('audit-778c731002de', 'student-001', 'student-001', 'STUDENT', 'RECOMMENDATION_CREATED', 'recommendation_session', 'a52369b6-c062-46ba-b083-016e2e8aa22a', '{}', '{}', NULL, NULL, 'recommendation:a52369b6-c062-46ba-b083-016e2e8aa22a', '2026-07-16 18:16:23.578919');
INSERT INTO `audit_logs` VALUES ('audit-7d068d6e3041', 'student-001', 'student-001', 'STUDENT', 'ENROLLMENT_DROPPED', 'enrollment', 'enrollment-001', '{\"status\": \"ENROLLED\", \"course_id\": \"course-101\"}', '{\"status\": \"DROPPED\", \"course_id\": \"course-101\"}', NULL, NULL, 'student:student-001:course-101', '2026-07-16 18:59:21.016961');
INSERT INTO `audit_logs` VALUES ('audit-9ad2410bf53b', 'student-001', 'student-001', 'STUDENT', 'RECOMMENDATION_CREATED', 'recommendation_session', '3c22a7dc-6312-4c73-9d62-d13ab9a09581', '{}', '{}', NULL, NULL, 'recommendation:3c22a7dc-6312-4c73-9d62-d13ab9a09581', '2026-07-16 18:48:13.163758');
INSERT INTO `audit_logs` VALUES ('audit-bafc5510091e', 'student-001', 'student-001', 'STUDENT', 'RECOMMENDATION_CREATED', 'recommendation_session', '10ca507a-d692-4c60-81e3-5c037b0a4e1d', '{}', '{}', NULL, NULL, 'recommendation:10ca507a-d692-4c60-81e3-5c037b0a4e1d', '2026-07-16 19:48:06.986156');
INSERT INTO `audit_logs` VALUES ('audit-f6f6fc591fb9', 'student-001', 'student-001', 'STUDENT', 'ENROLLMENT_DROPPED', 'enrollment', 'enrollment-002', '{\"status\": \"ENROLLED\", \"course_id\": \"course-201\"}', '{\"status\": \"DROPPED\", \"course_id\": \"course-201\"}', NULL, NULL, 'student:student-001:course-201', '2026-07-16 18:17:56.693983');
-- ----------------------------
-- Table structure for course_operation_approvals
-- ----------------------------
DROP TABLE IF EXISTS `course_operation_approvals`;
CREATE TABLE `course_operation_approvals`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `operation` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `requester_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `reviewer_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING',
  `payload_json` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `comment` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `idempotency_key` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_course_operation_approvals_idempotency`(`idempotency_key` ASC) USING BTREE,
  INDEX `ix_course_operation_approvals_status_created`(`status` ASC, `created_at` ASC) USING BTREE,
  INDEX `ix_course_operation_approvals_course_status`(`course_id` ASC, `status` ASC) USING BTREE,
  INDEX `fk_course_operation_approvals_requester`(`requester_id` ASC) USING BTREE,
  INDEX `fk_course_operation_approvals_reviewer`(`reviewer_id` ASC) USING BTREE,
  CONSTRAINT `fk_course_operation_approvals_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_course_operation_approvals_requester` FOREIGN KEY (`requester_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_course_operation_approvals_reviewer` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of course_operation_approvals
-- ----------------------------
-- ----------------------------
-- Table structure for course_prerequisites
-- ----------------------------
DROP TABLE IF EXISTS `course_prerequisites`;
CREATE TABLE `course_prerequisites`  (
  `course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `prerequisite_course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `min_grade` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'D',
  PRIMARY KEY (`course_id`, `prerequisite_course_id`) USING BTREE,
  INDEX `ix_course_prerequisites_prereq`(`prerequisite_course_id` ASC) USING BTREE,
  CONSTRAINT `fk_course_prerequisites_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_course_prerequisites_required` FOREIGN KEY (`prerequisite_course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of course_prerequisites
-- ----------------------------
INSERT INTO `course_prerequisites` VALUES ('course-201', 'course-101', 'D');
-- ----------------------------
-- Table structure for course_rules
-- ----------------------------
DROP TABLE IF EXISTS `course_rules`;
CREATE TABLE `course_rules`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `rule_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_json` json NOT NULL,
  `enabled` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `ix_course_rules_course_enabled`(`course_id` ASC, `enabled` ASC) USING BTREE,
  CONSTRAINT `fk_course_rules_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of course_rules
-- ----------------------------
INSERT INTO `course_rules` VALUES ('rule-201-major', 'course-201', 'MAJOR', '{\"allowed_majors\": [\"Computer Science\", \"Artificial Intelligence\"]}', 1);
-- ----------------------------
-- Table structure for course_schedules
-- ----------------------------
DROP TABLE IF EXISTS `course_schedules`;
CREATE TABLE `course_schedules`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `weekday` int NOT NULL,
  `start_minute` int NOT NULL,
  `end_minute` int NOT NULL,
  `room` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'TBD',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `ix_course_schedules_course_time`(`course_id` ASC, `weekday` ASC, `start_minute` ASC) USING BTREE,
  CONSTRAINT `fk_course_schedules_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of course_schedules
-- ----------------------------
INSERT INTO `course_schedules` VALUES ('schedule-101', 'course-101', 1, 480, 570, 'A101');
INSERT INTO `course_schedules` VALUES ('schedule-201', 'course-201', 2, 600, 690, 'B201');
INSERT INTO `course_schedules` VALUES ('schedule-301', 'course-301', 3, 480, 570, 'C301');
INSERT INTO `course_schedules` VALUES ('schedule-401', 'course-401', 1, 480, 570, 'D401');
INSERT INTO `course_schedules` VALUES ('schedule-401b', 'course-401', 3, 480, 570, 'D401');
INSERT INTO `course_schedules` VALUES ('schedule-402', 'course-402', 2, 600, 690, 'D402');
INSERT INTO `course_schedules` VALUES ('schedule-402b', 'course-402', 4, 600, 690, 'D402');
INSERT INTO `course_schedules` VALUES ('schedule-403', 'course-403', 3, 600, 690, 'D403');
INSERT INTO `course_schedules` VALUES ('schedule-403b', 'course-403', 5, 600, 690, 'D403');
INSERT INTO `course_schedules` VALUES ('schedule-404', 'course-404', 1, 600, 690, 'D404');
INSERT INTO `course_schedules` VALUES ('schedule-404b', 'course-404', 3, 600, 690, 'D404');
INSERT INTO `course_schedules` VALUES ('schedule-405', 'course-405', 4, 480, 570, 'D405');
INSERT INTO `course_schedules` VALUES ('schedule-406', 'course-406', 2, 720, 810, 'D406');
INSERT INTO `course_schedules` VALUES ('schedule-406b', 'course-406', 4, 720, 810, 'D406');
INSERT INTO `course_schedules` VALUES ('schedule-407', 'course-407', 5, 480, 570, 'D407');
INSERT INTO `course_schedules` VALUES ('schedule-408', 'course-408', 1, 720, 810, 'D408');
INSERT INTO `course_schedules` VALUES ('schedule-408b', 'course-408', 3, 720, 810, 'D408');
INSERT INTO `course_schedules` VALUES ('schedule-409', 'course-409', 2, 480, 570, 'D409');
INSERT INTO `course_schedules` VALUES ('schedule-409b', 'course-409', 4, 480, 570, 'D409');
INSERT INTO `course_schedules` VALUES ('schedule-410', 'course-410', 3, 720, 810, 'D410');
INSERT INTO `course_schedules` VALUES ('schedule-410b', 'course-410', 5, 720, 810, 'D410');
INSERT INTO `course_schedules` VALUES ('schedule-501', 'course-501', 1, 480, 570, 'E501');
INSERT INTO `course_schedules` VALUES ('schedule-501b', 'course-501', 3, 480, 570, 'E501');
INSERT INTO `course_schedules` VALUES ('schedule-502', 'course-502', 2, 600, 690, 'E502');
INSERT INTO `course_schedules` VALUES ('schedule-502b', 'course-502', 4, 600, 690, 'E502');
INSERT INTO `course_schedules` VALUES ('schedule-503', 'course-503', 3, 600, 690, 'E503');
INSERT INTO `course_schedules` VALUES ('schedule-503b', 'course-503', 5, 600, 690, 'E503');
INSERT INTO `course_schedules` VALUES ('schedule-504', 'course-504', 1, 600, 690, 'E504');
INSERT INTO `course_schedules` VALUES ('schedule-504b', 'course-504', 3, 600, 690, 'E504');
INSERT INTO `course_schedules` VALUES ('schedule-505', 'course-505', 4, 480, 570, 'E505');
INSERT INTO `course_schedules` VALUES ('schedule-505b', 'course-505', 5, 480, 570, 'E505');
INSERT INTO `course_schedules` VALUES ('schedule-506', 'course-506', 2, 720, 810, 'E506');
INSERT INTO `course_schedules` VALUES ('schedule-506b', 'course-506', 4, 720, 810, 'E506');
INSERT INTO `course_schedules` VALUES ('schedule-507', 'course-507', 1, 720, 810, 'E507');
INSERT INTO `course_schedules` VALUES ('schedule-508', 'course-508', 3, 720, 810, 'E508');
INSERT INTO `course_schedules` VALUES ('schedule-508b', 'course-508', 5, 720, 810, 'E508');
INSERT INTO `course_schedules` VALUES ('schedule-509', 'course-509', 2, 480, 570, 'E509');
INSERT INTO `course_schedules` VALUES ('schedule-509b', 'course-509', 4, 480, 570, 'E509');
INSERT INTO `course_schedules` VALUES ('schedule-510', 'course-510', 5, 600, 690, 'E510');
INSERT INTO `course_schedules` VALUES ('schedule-601', 'course-601', 1, 480, 570, 'F601');
INSERT INTO `course_schedules` VALUES ('schedule-601b', 'course-601', 3, 480, 570, 'F601');
INSERT INTO `course_schedules` VALUES ('schedule-601c', 'course-601', 5, 480, 570, 'F601');
INSERT INTO `course_schedules` VALUES ('schedule-602', 'course-602', 2, 600, 690, 'F602');
INSERT INTO `course_schedules` VALUES ('schedule-602b', 'course-602', 4, 600, 690, 'F602');
INSERT INTO `course_schedules` VALUES ('schedule-602c', 'course-602', 5, 600, 690, 'F602');
INSERT INTO `course_schedules` VALUES ('schedule-603', 'course-603', 1, 600, 690, 'F603');
INSERT INTO `course_schedules` VALUES ('schedule-603b', 'course-603', 3, 600, 690, 'F603');
INSERT INTO `course_schedules` VALUES ('schedule-603c', 'course-603', 5, 600, 690, 'F603');
INSERT INTO `course_schedules` VALUES ('schedule-604', 'course-604', 2, 480, 570, 'F604');
INSERT INTO `course_schedules` VALUES ('schedule-604b', 'course-604', 4, 480, 570, 'F604');
INSERT INTO `course_schedules` VALUES ('schedule-605', 'course-605', 1, 720, 810, 'F605');
INSERT INTO `course_schedules` VALUES ('schedule-605b', 'course-605', 3, 720, 810, 'F605');
INSERT INTO `course_schedules` VALUES ('schedule-606', 'course-606', 2, 720, 810, 'F606');
INSERT INTO `course_schedules` VALUES ('schedule-606b', 'course-606', 4, 720, 810, 'F606');
INSERT INTO `course_schedules` VALUES ('schedule-607', 'course-607', 5, 720, 810, 'F607');
INSERT INTO `course_schedules` VALUES ('schedule-608', 'course-608', 4, 720, 810, 'F608');
INSERT INTO `course_schedules` VALUES ('schedule-609', 'course-609', 3, 840, 960, 'F609');
INSERT INTO `course_schedules` VALUES ('schedule-610', 'course-610', 5, 840, 960, 'F610');
INSERT INTO `course_schedules` VALUES ('schedule-701', 'course-701', 1, 480, 570, 'G701');
INSERT INTO `course_schedules` VALUES ('schedule-701b', 'course-701', 3, 480, 570, 'G701');
INSERT INTO `course_schedules` VALUES ('schedule-702', 'course-702', 2, 600, 690, 'G702');
INSERT INTO `course_schedules` VALUES ('schedule-702b', 'course-702', 4, 600, 690, 'G702');
INSERT INTO `course_schedules` VALUES ('schedule-703', 'course-703', 3, 600, 690, 'G703');
INSERT INTO `course_schedules` VALUES ('schedule-703b', 'course-703', 5, 600, 690, 'G703');
INSERT INTO `course_schedules` VALUES ('schedule-704', 'course-704', 1, 600, 690, 'G704');
INSERT INTO `course_schedules` VALUES ('schedule-704b', 'course-704', 3, 600, 690, 'G704');
INSERT INTO `course_schedules` VALUES ('schedule-705', 'course-705', 4, 480, 570, 'G705');
INSERT INTO `course_schedules` VALUES ('schedule-705b', 'course-705', 5, 480, 570, 'G705');
INSERT INTO `course_schedules` VALUES ('schedule-706', 'course-706', 2, 720, 810, 'G706');
INSERT INTO `course_schedules` VALUES ('schedule-706b', 'course-706', 4, 720, 810, 'G706');
INSERT INTO `course_schedules` VALUES ('schedule-707', 'course-707', 1, 720, 810, 'G707');
INSERT INTO `course_schedules` VALUES ('schedule-707b', 'course-707', 3, 720, 810, 'G707');
INSERT INTO `course_schedules` VALUES ('schedule-708', 'course-708', 2, 480, 570, 'G708');
INSERT INTO `course_schedules` VALUES ('schedule-709', 'course-709', 5, 720, 810, 'G709');
INSERT INTO `course_schedules` VALUES ('schedule-710', 'course-710', 4, 720, 810, 'G710');
INSERT INTO `course_schedules` VALUES ('schedule-801', 'course-801', 1, 480, 570, 'H801');
INSERT INTO `course_schedules` VALUES ('schedule-801b', 'course-801', 3, 480, 570, 'H801');
INSERT INTO `course_schedules` VALUES ('schedule-802', 'course-802', 2, 600, 690, 'H802');
INSERT INTO `course_schedules` VALUES ('schedule-802b', 'course-802', 4, 600, 690, 'H802');
INSERT INTO `course_schedules` VALUES ('schedule-803', 'course-803', 3, 600, 690, 'H803');
INSERT INTO `course_schedules` VALUES ('schedule-804', 'course-804', 1, 600, 690, 'H804');
INSERT INTO `course_schedules` VALUES ('schedule-804b', 'course-804', 3, 600, 690, 'H804');
INSERT INTO `course_schedules` VALUES ('schedule-805', 'course-805', 4, 480, 570, 'H805');
INSERT INTO `course_schedules` VALUES ('schedule-806', 'course-806', 5, 480, 570, 'H806');
INSERT INTO `course_schedules` VALUES ('schedule-807', 'course-807', 2, 720, 810, 'H807');
INSERT INTO `course_schedules` VALUES ('schedule-807b', 'course-807', 4, 720, 810, 'H807');
INSERT INTO `course_schedules` VALUES ('schedule-808', 'course-808', 5, 600, 690, 'H808');
INSERT INTO `course_schedules` VALUES ('schedule-809', 'course-809', 1, 480, 570, 'H809');
INSERT INTO `course_schedules` VALUES ('schedule-810', 'course-810', 2, 600, 690, 'H810');
INSERT INTO `course_schedules` VALUES ('schedule-811', 'course-811', 3, 480, 570, 'H811');
INSERT INTO `course_schedules` VALUES ('schedule-812', 'course-812', 4, 600, 690, 'H812');
INSERT INTO `course_schedules` VALUES ('schedule-813', 'course-813', 5, 480, 570, 'H813');
INSERT INTO `course_schedules` VALUES ('schedule-814', 'course-814', 1, 720, 810, 'H814');
INSERT INTO `course_schedules` VALUES ('schedule-815', 'course-815', 2, 480, 570, 'H815');
INSERT INTO `course_schedules` VALUES ('schedule-816', 'course-816', 3, 720, 810, 'H816');
INSERT INTO `course_schedules` VALUES ('schedule-901', 'course-901', 1, 480, 570, 'I901');
INSERT INTO `course_schedules` VALUES ('schedule-902', 'course-902', 2, 480, 570, 'I902');
INSERT INTO `course_schedules` VALUES ('schedule-903', 'course-903', 3, 480, 570, 'I903');
INSERT INTO `course_schedules` VALUES ('schedule-904', 'course-904', 4, 480, 570, 'I904');
INSERT INTO `course_schedules` VALUES ('schedule-905', 'course-905', 5, 480, 570, 'I905');
INSERT INTO `course_schedules` VALUES ('schedule-906', 'course-906', 1, 600, 690, 'I906');
INSERT INTO `course_schedules` VALUES ('schedule-907', 'course-907', 3, 600, 690, 'I907');
INSERT INTO `course_schedules` VALUES ('schedule-908', 'course-908', 2, 600, 690, 'I908');
INSERT INTO `course_schedules` VALUES ('schedule-909', 'course-909', 4, 600, 690, 'I909');
INSERT INTO `course_schedules` VALUES ('schedule-910', 'course-910', 5, 600, 690, 'I910');
INSERT INTO `course_schedules` VALUES ('schedule-A01', 'course-A01', 1, 840, 930, 'Gym-A');
INSERT INTO `course_schedules` VALUES ('schedule-A02', 'course-A02', 2, 840, 930, 'Gym-B');
INSERT INTO `course_schedules` VALUES ('schedule-A03', 'course-A03', 3, 840, 930, 'Gym-A');
INSERT INTO `course_schedules` VALUES ('schedule-A04', 'course-A04', 4, 840, 930, 'Gym-C');
INSERT INTO `course_schedules` VALUES ('schedule-A05', 'course-A05', 5, 840, 930, 'Gym-C');
INSERT INTO `course_schedules` VALUES ('schedule-A06', 'course-A06', 1, 960, 1050, 'Gym-B');
INSERT INTO `course_schedules` VALUES ('schedule-A07', 'course-A07', 2, 960, 1050, 'Pool');
INSERT INTO `course_schedules` VALUES ('schedule-A08', 'course-A08', 3, 960, 1050, 'Gym-A');
INSERT INTO `course_schedules` VALUES ('schedule-A09', 'course-A09', 4, 960, 1050, 'Gym-B');
INSERT INTO `course_schedules` VALUES ('schedule-A10', 'course-A10', 5, 960, 1050, 'Gym-A');
INSERT INTO `course_schedules` VALUES ('schedule-B01', 'course-B01', 1, 480, 570, 'J101');
INSERT INTO `course_schedules` VALUES ('schedule-B01b', 'course-B01', 3, 480, 570, 'J101');
INSERT INTO `course_schedules` VALUES ('schedule-B02', 'course-B02', 2, 480, 570, 'J102');
INSERT INTO `course_schedules` VALUES ('schedule-B02b', 'course-B02', 4, 480, 570, 'J102');
INSERT INTO `course_schedules` VALUES ('schedule-B03', 'course-B03', 1, 600, 690, 'J103');
INSERT INTO `course_schedules` VALUES ('schedule-B03b', 'course-B03', 3, 600, 690, 'J103');
INSERT INTO `course_schedules` VALUES ('schedule-B04', 'course-B04', 2, 600, 690, 'J104');
INSERT INTO `course_schedules` VALUES ('schedule-B04b', 'course-B04', 4, 600, 690, 'J104');
INSERT INTO `course_schedules` VALUES ('schedule-B05', 'course-B05', 5, 480, 570, 'J105');
INSERT INTO `course_schedules` VALUES ('schedule-B05b', 'course-B05', 1, 720, 810, 'J105');
INSERT INTO `course_schedules` VALUES ('schedule-B06', 'course-B06', 3, 720, 810, 'J106');
INSERT INTO `course_schedules` VALUES ('schedule-B07', 'course-B07', 4, 720, 810, 'J107');
INSERT INTO `course_schedules` VALUES ('schedule-B08', 'course-B08', 2, 720, 810, 'J108');
INSERT INTO `course_schedules` VALUES ('schedule-B09', 'course-B09', 5, 720, 810, 'J109');
INSERT INTO `course_schedules` VALUES ('schedule-B10', 'course-B10', 4, 960, 1050, 'J110');
INSERT INTO `course_schedules` VALUES ('schedule-C01', 'course-C01', 1, 480, 570, 'K101');
INSERT INTO `course_schedules` VALUES ('schedule-C01b', 'course-C01', 3, 480, 570, 'K101');
INSERT INTO `course_schedules` VALUES ('schedule-C02', 'course-C02', 2, 600, 690, 'K102');
INSERT INTO `course_schedules` VALUES ('schedule-C02b', 'course-C02', 4, 600, 690, 'K102');
INSERT INTO `course_schedules` VALUES ('schedule-C03', 'course-C03', 1, 600, 690, 'K103');
INSERT INTO `course_schedules` VALUES ('schedule-C03b', 'course-C03', 3, 600, 690, 'K103');
INSERT INTO `course_schedules` VALUES ('schedule-C04', 'course-C04', 5, 480, 570, 'K104');
INSERT INTO `course_schedules` VALUES ('schedule-C05', 'course-C05', 4, 600, 690, 'K105');
INSERT INTO `course_schedules` VALUES ('schedule-C05b', 'course-C05', 5, 600, 690, 'K105');
INSERT INTO `course_schedules` VALUES ('schedule-C06', 'course-C06', 2, 480, 570, 'K106');
INSERT INTO `course_schedules` VALUES ('schedule-C07', 'course-C07', 1, 720, 810, 'K107');
INSERT INTO `course_schedules` VALUES ('schedule-C07b', 'course-C07', 3, 720, 810, 'K107');
INSERT INTO `course_schedules` VALUES ('schedule-C08', 'course-C08', 2, 720, 810, 'K108');
INSERT INTO `course_schedules` VALUES ('schedule-C09', 'course-C09', 4, 720, 810, 'K109');
INSERT INTO `course_schedules` VALUES ('schedule-C10', 'course-C10', 5, 720, 810, 'K110');
-- ----------------------------
-- Table structure for courses
-- ----------------------------
DROP TABLE IF EXISTS `courses`;
CREATE TABLE `courses`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `teacher_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `credits` int NOT NULL,
  `capacity` int NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'OPEN',
  `version` int NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_courses_code`(`code` ASC) USING BTREE,
  INDEX `ix_courses_status_code`(`status` ASC, `code` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of courses
-- ----------------------------
INSERT INTO `courses` VALUES ('course-101', 'CS101', '程序设计基础', '王老师', 3, 2, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-201', 'AI201', '人工智能导论', '李老师', 3, 1, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-301', 'SE301', '软件工程实践', '周老师', 3, 3, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-401', 'CS401', '编译原理', '吴老师', 3, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-402', 'CS402', '计算机图形学', '郑老师', 3, 45, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-403', 'CS403', '自然语言处理', '冯老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-404', 'CS404', '计算机视觉', '陈老师', 3, 45, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-405', 'CS405', '信息检索', '褚老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-406', 'CS406', '数字图像处理', '卫老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-407', 'CS407', '多媒体技术', '蒋老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-408', 'CS408', '嵌入式系统', '沈老师', 3, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-409', 'CS409', '并行计算', '韩老师', 3, 45, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-410', 'CS410', '分布式系统', '杨老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-501', 'MATH501', '实变函数', '朱老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-502', 'MATH502', '泛函分析', '秦老师', 3, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-503', 'MATH503', '近世代数', '尤老师', 3, 45, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-504', 'MATH504', '微分几何', '许老师', 3, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-505', 'MATH505', '拓扑学', '何老师', 3, 35, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-506', 'MATH506', '数理方程', '吕老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-507', 'MATH507', '复变函数', '施老师', 3, 55, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-508', 'MATH508', '数值分析', '张老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-509', 'MATH509', '随机过程', '孔老师', 3, 45, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-510', 'MATH510', '数学建模', '曹老师', 3, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-601', 'PHY601', '量子力学', '严老师', 4, 45, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-602', 'PHY602', '热力学与统计物理', '华老师', 4, 45, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-603', 'PHY603', '电动力学', '金老师', 4, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-604', 'PHY604', '固体物理', '魏老师', 3, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-605', 'PHY605', '光学', '陶老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-606', 'PHY606', '原子物理学', '姜老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-607', 'PHY607', '核物理概论', '戚老师', 2, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-608', 'PHY608', '天体物理导论', '谢老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-609', 'PHY609', '大学物理实验(上)', '邹老师', 1, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-610', 'PHY610', '大学物理实验(下)', '邹老师', 1, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-701', 'EE701', '信号与系统', '喻老师', 3, 55, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-702', 'EE702', '通信原理', '柏老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-703', 'EE703', '电磁场与电磁波', '窦老师', 3, 45, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-704', 'EE704', '数字信号处理', '章老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-705', 'EE705', '微机原理与接口', '苏老师', 3, 45, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-706', 'EE706', '自动控制原理', '潘老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-707', 'EE707', '电力电子技术', '葛老师', 3, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-708', 'EE708', '传感器与检测技术', '奚老师', 2, 45, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-709', 'EE709', '电机与拖动基础', '范老师', 3, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-710', 'EE710', 'FPGA设计基础', '彭老师', 2, 35, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-801', 'ECON801', '国际经济学', '郎老师', 3, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-802', 'ECON802', '发展经济学', '鲁老师', 3, 55, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-803', 'ECON803', '博弈论基础', '韦老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-804', 'ECON804', '货币银行学', '昌老师', 3, 55, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-805', 'ECON805', '财政学', '马老师', 3, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-806', 'ECON806', '经济法', '苗老师', 2, 70, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-807', 'ECON807', '计量经济学', '凤老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-808', 'ECON808', '产业经济学', '花老师', 3, 55, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-809', 'MGMT801', '人力资源管理', '方老师', 2, 70, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-810', 'MGMT802', '战略管理', '俞老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-811', 'MGMT803', '供应链管理', '任老师', 2, 55, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-812', 'MGMT804', '项目管理', '袁老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-813', 'MGMT805', '创业管理', '柳老师', 2, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-814', 'MGMT806', '质量管理', '酆老师', 2, 55, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-815', 'MGMT807', '组织行为学', '鲍老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-816', 'MGMT808', '管理信息系统', '史老师', 2, 55, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-901', 'LANG901', '大学英语(一)', '唐老师', 2, 120, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-902', 'LANG902', '大学英语(二)', '费老师', 2, 120, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-903', 'LANG903', '大学英语(三)', '廉老师', 2, 100, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-904', 'LANG904', '大学英语(四)', '岑老师', 2, 100, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-905', 'LANG905', '学术英语写作', '薛老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-906', 'LANG906', '英语视听说', '雷老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-907', 'LANG907', '商务英语', '贺老师', 2, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-908', 'LANG908', '日语(一)', '倪老师', 2, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-909', 'LANG909', '法语入门', '汤老师', 2, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-910', 'LANG910', '德语入门', '滕老师', 2, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-A01', 'PE001', '篮球', '殷老师', 1, 30, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-A02', 'PE002', '足球', '罗老师', 1, 30, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-A03', 'PE003', '排球', '毕老师', 1, 30, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-A04', 'PE004', '羽毛球', '郝老师', 1, 25, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-A05', 'PE005', '乒乓球', '邬老师', 1, 25, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-A06', 'PE006', '网球', '安老师', 1, 25, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-A07', 'PE007', '游泳', '常老师', 1, 20, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-A08', 'PE008', '太极拳', '乐老师', 1, 40, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-A09', 'PE009', '健美操', '于老师', 1, 35, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-A10', 'PE010', '体育舞蹈', '时老师', 1, 30, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-B01', 'POL101', '思想道德与法治', '傅老师', 3, 120, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-B02', 'POL102', '中国近现代史纲要', '皮老师', 3, 120, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-B03', 'POL103', '马克思主义基本原理', '卞老师', 3, 100, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-B04', 'POL104', '毛泽东思想和中国特色社会主义理论体系概论', '齐老师', 3, 100, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-B05', 'POL105', '习近平新时代中国特色社会主义思想概论', '康老师', 3, 100, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-B06', 'POL106', '形势与政策(一)', '伍老师', 1, 120, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-B07', 'POL107', '形势与政策(二)', '余老师', 1, 120, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-B08', 'HIST101', '中华文明史', '元老师', 2, 80, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-B09', 'PHIL101', '逻辑学导论', '卜老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-B10', 'PSY101', '心理学导论', '顾老师', 2, 80, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-C01', 'CHEM101', '普通化学', '孟老师', 3, 80, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-C02', 'CHEM102', '有机化学', '平老师', 3, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-C03', 'BIO101', '普通生物学', '黄老师', 3, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-C04', 'ENV101', '环境科学导论', '穆老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-C05', 'MAT101', '材料科学基础', '萧老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-C06', 'DS101', '数据科学导论', '尹老师', 2, 60, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-C07', 'DS102', '大数据技术基础', '姚老师', 3, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-C08', 'SE101', '软件需求工程', '邵老师', 2, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-C09', 'SE102', '软件测试与质量保证', '湛老师', 2, 50, 'OPEN', 1);
INSERT INTO `courses` VALUES ('course-C10', 'IS101', '信息安全导论', '汪老师', 2, 60, 'OPEN', 1);
-- ----------------------------
-- Table structure for enrollment_requests
-- ----------------------------
DROP TABLE IF EXISTS `enrollment_requests`;
CREATE TABLE `enrollment_requests`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `idempotency_key` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_enrollment_requests_idempotency`(`idempotency_key` ASC) USING BTREE,
  INDEX `ix_enrollment_requests_student_created`(`student_id` ASC, `created_at` ASC) USING BTREE,
  INDEX `fk_enrollment_requests_course`(`course_id` ASC) USING BTREE,
  CONSTRAINT `fk_enrollment_requests_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_enrollment_requests_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of enrollment_requests
-- ----------------------------
INSERT INTO `enrollment_requests` VALUES ('23750e88-01d4-494f-ae5c-0cc721229a42', 'student-001', 'course-301', 'ENROLL', 'COMPLETED', 'ENROLLED', NULL, '2026-07-16 19:00:02.010999');
INSERT INTO `enrollment_requests` VALUES ('25bbdc96-3a91-4e80-ae9c-418fce1d5e61', 'student-001', 'course-101', 'ENROLL', 'COMPLETED', 'ENROLLED', NULL, '2026-07-16 18:48:07.511072');
INSERT INTO `enrollment_requests` VALUES ('39d6af3c-9f0b-4aa7-969e-33b4142d2e6b', 'student-001', 'course-301', 'ENROLL', 'COMPLETED', 'ENROLLED', NULL, '2026-07-16 19:00:02.012998');
INSERT INTO `enrollment_requests` VALUES ('4f2e4ff2-b70f-4ae3-9a35-bc56d9459411', 'student-001', 'course-101', 'DROP', 'COMPLETED', 'DROPPED', NULL, '2026-07-16 18:48:00.333159');
INSERT INTO `enrollment_requests` VALUES ('a3502b61-3abc-4563-bbfe-4357e91cd451', 'student-001', 'course-101', 'ENROLL', 'COMPLETED', 'ENROLLED', NULL, '2026-07-16 18:48:07.513071');
INSERT INTO `enrollment_requests` VALUES ('b9d6bc1e-16b6-4278-ae80-22360dea9c4d', 'student-001', 'course-101', 'DROP', 'COMPLETED', 'DROPPED', NULL, '2026-07-16 18:59:21.019473');
INSERT INTO `enrollment_requests` VALUES ('efad9372-b711-4fc1-9b5e-e8fb3ac1a939', 'student-001', 'course-201', 'DROP', 'COMPLETED', 'DROPPED', NULL, '2026-07-16 18:17:56.698333');
INSERT INTO `enrollment_requests` VALUES ('request-001', 'student-001', 'course-101', 'ENROLL', 'COMPLETED', 'ENROLLED', 'seed-enroll-001', '2026-07-16 18:14:54.711373');
INSERT INTO `enrollment_requests` VALUES ('request-002', 'student-002', 'course-201', 'WAITLIST', 'COMPLETED', 'WAITING', 'seed-waitlist-001', '2026-07-16 18:14:54.711373');
-- ----------------------------
-- Table structure for enrollments
-- ----------------------------
DROP TABLE IF EXISTS `enrollments`;
CREATE TABLE `enrollments`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `source` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'DIRECT',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_enrollment_student_course`(`student_id` ASC, `course_id` ASC) USING BTREE,
  INDEX `ix_enrollments_course_status`(`course_id` ASC, `status` ASC) USING BTREE,
  INDEX `ix_enrollments_student_status`(`student_id` ASC, `status` ASC) USING BTREE,
  CONSTRAINT `fk_enrollments_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_enrollments_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of enrollments
-- ----------------------------
INSERT INTO `enrollments` VALUES ('ab287e0a-6a36-40e1-8974-56d1edb431cc', 'student-001', 'course-301', 'ENROLLED', 'DIRECT', '2026-07-16 19:00:02.009998', '2026-07-16 19:00:02.009998');
INSERT INTO `enrollments` VALUES ('enrollment-001', 'student-001', 'course-101', 'DROPPED', 'DIRECT', '2026-07-16 18:14:54.710197', '2026-07-16 18:59:21.017963');
INSERT INTO `enrollments` VALUES ('enrollment-002', 'student-001', 'course-201', 'DROPPED', 'DIRECT', '2026-07-16 18:14:54.710197', '2026-07-16 18:17:56.695992');
INSERT INTO `enrollments` VALUES ('enrollment-003', 'student-003', 'course-101', 'ENROLLED', 'DIRECT', '2026-07-16 18:14:54.710197', '2026-07-16 18:14:54.710197');
-- ----------------------------
-- Table structure for exception_approvals
-- ----------------------------
DROP TABLE IF EXISTS `exception_approvals`;
CREATE TABLE `exception_approvals`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `request_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `enrollment_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `student_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING',
  `rule_violations` json NOT NULL,
  `reviewer_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `comment` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `waived_rules` json NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `ix_exception_approvals_status_created`(`status` ASC, `created_at` ASC) USING BTREE,
  INDEX `ix_exception_approvals_course_student`(`course_id` ASC, `student_id` ASC) USING BTREE,
  INDEX `fk_exception_approvals_request`(`request_id` ASC) USING BTREE,
  INDEX `fk_exception_approvals_enrollment`(`enrollment_id` ASC) USING BTREE,
  INDEX `fk_exception_approvals_student`(`student_id` ASC) USING BTREE,
  INDEX `fk_exception_approvals_reviewer`(`reviewer_id` ASC) USING BTREE,
  CONSTRAINT `fk_exception_approvals_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_exception_approvals_enrollment` FOREIGN KEY (`enrollment_id`) REFERENCES `enrollments` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_exception_approvals_request` FOREIGN KEY (`request_id`) REFERENCES `enrollment_requests` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_exception_approvals_reviewer` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_exception_approvals_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of exception_approvals
-- ----------------------------
INSERT INTO `exception_approvals` VALUES ('approval-001', NULL, NULL, 'student-002', 'course-201', 'PENDING', '[\"PREREQUISITE_MISSING\"]', NULL, '请核查先修课程例外', '[]', '2026-07-16 18:14:54.711989', '2026-07-16 18:14:54.711989');
-- ----------------------------
-- Table structure for recalculation_results
-- ----------------------------
DROP TABLE IF EXISTS `recalculation_results`;
CREATE TABLE `recalculation_results`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `run_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_id` varchar(72) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `old_status` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `new_status` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `reason_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `details_json` json NOT NULL,
  `occurred_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `ix_recalculation_results_run`(`run_id` ASC, `occurred_at` ASC, `id` ASC) USING BTREE,
  INDEX `fk_recalculation_results_student`(`student_id` ASC) USING BTREE,
  CONSTRAINT `fk_recalculation_results_run` FOREIGN KEY (`run_id`) REFERENCES `recalculation_runs` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_recalculation_results_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of recalculation_results
-- ----------------------------
-- ----------------------------
-- Table structure for recalculation_runs
-- ----------------------------
DROP TABLE IF EXISTS `recalculation_runs`;
CREATE TABLE `recalculation_runs`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `trigger_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `operator_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING',
  `idempotency_key` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `summary_json` json NOT NULL,
  `error_json` json NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `started_at` datetime(6) NULL DEFAULT NULL,
  `finished_at` datetime(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_recalculation_runs_idempotency`(`idempotency_key` ASC) USING BTREE,
  INDEX `ix_recalculation_runs_course_status`(`course_id` ASC, `status` ASC) USING BTREE,
  INDEX `ix_recalculation_runs_created`(`created_at` ASC) USING BTREE,
  INDEX `fk_recalculation_runs_operator`(`operator_id` ASC) USING BTREE,
  CONSTRAINT `fk_recalculation_runs_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_recalculation_runs_operator` FOREIGN KEY (`operator_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of recalculation_runs
-- ----------------------------
-- ----------------------------
-- Table structure for recommendation_items
-- ----------------------------
DROP TABLE IF EXISTS `recommendation_items`;
CREATE TABLE `recommendation_items`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `rank` int NOT NULL,
  `reasons_json` json NOT NULL,
  `uncertainties_json` json NOT NULL,
  `eligibility_json` json NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_recommendation_items_rank`(`session_id` ASC, `rank` ASC) USING BTREE,
  INDEX `ix_recommendation_items_course`(`course_id` ASC) USING BTREE,
  CONSTRAINT `fk_recommendation_items_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_recommendation_items_session` FOREIGN KEY (`session_id`) REFERENCES `recommendation_sessions` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of recommendation_items
-- ----------------------------
INSERT INTO `recommendation_items` VALUES ('13b3b915-5894-416f-bd61-afbfb581ee23', '8a293702-bf1c-45a1-b8cb-4ea6342a3bcf', 'course-301', 1, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"DUPLICATE\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T19:36:40.234862+00:00\", \"violations\": [{\"code\": \"DUPLICATE\", \"message\": \"已存在有效选课或候补记录\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('1cc6556e-6d64-4fe1-b422-1249d940f796', '3c22a7dc-6312-4c73-9d62-d13ab9a09581', 'course-301', 1, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"ELIGIBLE\", \"eligible\": true, \"warnings\": [], \"checked_at\": \"2026-07-16T18:48:13.142130+00:00\", \"violations\": []}');
INSERT INTO `recommendation_items` VALUES ('2ebaf2c8-bd49-4ce0-ae4a-8f644e4e49b5', '48dc0e35-1eed-4ebf-9b9c-2ca5ac4f2862', 'course-201', 2, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"PREREQUISITE_MISSING\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T19:37:14.986959+00:00\", \"violations\": [{\"code\": \"PREREQUISITE_MISSING\", \"message\": \"缺少先修课程 course-101\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('5aa46737-7803-42fa-970b-36b5f7d886c6', '3c22a7dc-6312-4c73-9d62-d13ab9a09581', 'course-101', 3, '[\"课程属于当前开放的候选课程集合\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"DUPLICATE\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T18:48:13.163758+00:00\", \"violations\": [{\"code\": \"DUPLICATE\", \"message\": \"已存在有效选课或候补记录\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('5ab27ecd-f57f-44f3-bc0e-f8e4b8d4d618', '3c22a7dc-6312-4c73-9d62-d13ab9a09581', 'course-201', 2, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"ELIGIBLE\", \"eligible\": true, \"warnings\": [], \"checked_at\": \"2026-07-16T18:48:13.155758+00:00\", \"violations\": []}');
INSERT INTO `recommendation_items` VALUES ('5bb4c87c-a556-4072-99b5-f5d3f3cade0c', 'a52369b6-c062-46ba-b083-016e2e8aa22a', 'course-101', 3, '[\"课程属于当前开放的候选课程集合\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"DUPLICATE\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T18:16:23.577919+00:00\", \"violations\": [{\"code\": \"DUPLICATE\", \"message\": \"已存在有效选课或候补记录\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('5d667551-0631-479e-98d9-c8a035427956', '10ca507a-d692-4c60-81e3-5c037b0a4e1d', 'course-301', 2, '[\"软件工程实践与软件工程目标一致\", \"典型的实践课程，符合偏好\"]', '[\"该课程已被学生选入，重复推荐\", \"需确认是否已获得学分\"]', '{\"decision\": \"DUPLICATE\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T19:48:06.975335+00:00\", \"violations\": [{\"code\": \"DUPLICATE\", \"message\": \"已存在有效选课或候补记录\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('6afc1bb8-b25b-45c7-9763-5bf36b2d5c9c', '69343473-dcd3-40bc-b675-c2557455eb6e', 'course-201', 2, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"PREREQUISITE_MISSING\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T19:38:12.936822+00:00\", \"violations\": [{\"code\": \"PREREQUISITE_MISSING\", \"message\": \"缺少先修课程 course-101\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('70cd84a3-7715-4151-887f-b5380ec99511', '2104703e-da0a-4c95-be47-25f176cb89f9', 'course-301', 1, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"ELIGIBLE\", \"eligible\": true, \"warnings\": [], \"checked_at\": \"2026-07-16T18:59:11.783922+00:00\", \"violations\": []}');
INSERT INTO `recommendation_items` VALUES ('75b34d48-64d2-46b9-8776-9a27ba6379f4', '2104703e-da0a-4c95-be47-25f176cb89f9', 'course-101', 5, '[\"课程属于当前开放的候选课程集合\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"DUPLICATE\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T18:59:11.820436+00:00\", \"violations\": [{\"code\": \"DUPLICATE\", \"message\": \"已存在有效选课或候补记录\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('77e7887f-73c8-49a2-b8c3-e970e13fa4ad', 'a52369b6-c062-46ba-b083-016e2e8aa22a', 'course-301', 1, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"ELIGIBLE\", \"eligible\": true, \"warnings\": [], \"checked_at\": \"2026-07-16T18:16:23.553317+00:00\", \"violations\": []}');
INSERT INTO `recommendation_items` VALUES ('8126f076-3d32-4f62-a565-41d1809dd05c', '48dc0e35-1eed-4ebf-9b9c-2ca5ac4f2862', 'course-301', 1, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"DUPLICATE\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T19:37:14.972423+00:00\", \"violations\": [{\"code\": \"DUPLICATE\", \"message\": \"已存在有效选课或候补记录\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('8ab92f00-a98b-4f8b-bfb8-c94e07e5382f', '8a293702-bf1c-45a1-b8cb-4ea6342a3bcf', 'course-201', 2, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"PREREQUISITE_MISSING\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T19:36:40.250394+00:00\", \"violations\": [{\"code\": \"PREREQUISITE_MISSING\", \"message\": \"缺少先修课程 course-101\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('8d7bbed5-939c-49ec-9efb-b57357084bb2', '69343473-dcd3-40bc-b675-c2557455eb6e', 'course-301', 1, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"DUPLICATE\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T19:38:12.920035+00:00\", \"violations\": [{\"code\": \"DUPLICATE\", \"message\": \"已存在有效选课或候补记录\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('9d7da549-75ae-41d4-8690-dfc74b21e070', '10ca507a-d692-4c60-81e3-5c037b0a4e1d', 'course-201', 1, '[\"直接匹配人工智能目标\", \"实践导向课程\"]', '[\"是否有先修课程要求（程序设计基础）\", \"时间与已选课程无冲突，但需确认先修条件\"]', '{\"decision\": \"PREREQUISITE_MISSING\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T19:48:06.963773+00:00\", \"violations\": [{\"code\": \"PREREQUISITE_MISSING\", \"message\": \"缺少先修课程 course-101\", \"blocking\": true}]}');
INSERT INTO `recommendation_items` VALUES ('a0b6f972-482f-4e62-b3fc-3ce8e2ad07ad', '8a293702-bf1c-45a1-b8cb-4ea6342a3bcf', 'course-101', 7, '[\"课程属于当前开放的候选课程集合\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"ELIGIBLE\", \"eligible\": true, \"warnings\": [], \"checked_at\": \"2026-07-16T19:36:40.313651+00:00\", \"violations\": []}');
INSERT INTO `recommendation_items` VALUES ('ad6225f0-eb0e-4fec-b2f6-051fa3f02859', '48dc0e35-1eed-4ebf-9b9c-2ca5ac4f2862', 'course-101', 7, '[\"课程属于当前开放的候选课程集合\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"ELIGIBLE\", \"eligible\": true, \"warnings\": [], \"checked_at\": \"2026-07-16T19:37:15.048213+00:00\", \"violations\": []}');
INSERT INTO `recommendation_items` VALUES ('c7ca5354-6f94-4464-ac04-9600b8aefb0b', '69343473-dcd3-40bc-b675-c2557455eb6e', 'course-101', 7, '[\"课程属于当前开放的候选课程集合\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"ELIGIBLE\", \"eligible\": true, \"warnings\": [], \"checked_at\": \"2026-07-16T19:38:12.998498+00:00\", \"violations\": []}');
INSERT INTO `recommendation_items` VALUES ('d2c5317f-1926-4e85-b6e6-6803517c1cfe', '2104703e-da0a-4c95-be47-25f176cb89f9', 'course-201', 2, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"ELIGIBLE\", \"eligible\": true, \"warnings\": [], \"checked_at\": \"2026-07-16T18:59:11.793920+00:00\", \"violations\": []}');
INSERT INTO `recommendation_items` VALUES ('e3221bd5-ef48-438e-9f9c-86b05416a324', 'a52369b6-c062-46ba-b083-016e2e8aa22a', 'course-201', 2, '[\"课程名称或代码与学习目标/偏好中的关键词相关\"]', '[\"当前使用固定规则推荐，最终资格以提交选课时的实时检查为准\"]', '{\"decision\": \"DUPLICATE\", \"eligible\": false, \"warnings\": [], \"checked_at\": \"2026-07-16T18:16:23.568325+00:00\", \"violations\": [{\"code\": \"DUPLICATE\", \"message\": \"已存在有效选课或候补记录\", \"blocking\": true}]}');
-- ----------------------------
-- Table structure for recommendation_sessions
-- ----------------------------
DROP TABLE IF EXISTS `recommendation_sessions`;
CREATE TABLE `recommendation_sessions`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `input_json` json NOT NULL,
  `model` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'rule_fallback',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `ix_recommendation_sessions_student_created`(`student_id` ASC, `created_at` ASC) USING BTREE,
  CONSTRAINT `fk_recommendation_sessions_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of recommendation_sessions
-- ----------------------------
INSERT INTO `recommendation_sessions` VALUES ('10ca507a-d692-4c60-81e3-5c037b0a4e1d', 'student-001', '{\"goals\": \"希望学习人工智能与软件工程\", \"preferences\": [\"偏好实践课程\"]}', 'deepseek', 'COMPLETED', '2026-07-16 19:48:06.949204');
INSERT INTO `recommendation_sessions` VALUES ('2104703e-da0a-4c95-be47-25f176cb89f9', 'student-001', '{\"goals\": \"希望学习人工智能与软件工程\", \"preferences\": [\"偏好实践课程\"]}', 'rule_fallback', 'FALLBACK', '2026-07-16 18:59:11.772406');
INSERT INTO `recommendation_sessions` VALUES ('3c22a7dc-6312-4c73-9d62-d13ab9a09581', 'student-001', '{\"goals\": \"希望学习人工智能与软件工程\", \"preferences\": [\"偏好实践课程\"]}', 'rule_fallback', 'FALLBACK', '2026-07-16 18:48:13.130240');
INSERT INTO `recommendation_sessions` VALUES ('48dc0e35-1eed-4ebf-9b9c-2ca5ac4f2862', 'student-001', '{\"goals\": \"希望学习人工智能与软件工程\", \"preferences\": [\"偏好实践课程\"]}', 'rule_fallback', 'FALLBACK', '2026-07-16 19:37:14.957824');
INSERT INTO `recommendation_sessions` VALUES ('69343473-dcd3-40bc-b675-c2557455eb6e', 'student-001', '{\"goals\": \"希望学习人工智能与软件工程\", \"preferences\": [\"偏好实践课程\"]}', 'rule_fallback', 'FALLBACK', '2026-07-16 19:38:12.901351');
INSERT INTO `recommendation_sessions` VALUES ('8a293702-bf1c-45a1-b8cb-4ea6342a3bcf', 'student-001', '{\"goals\": \"希望学习人工智能与软件工程\", \"preferences\": [\"偏好实践课程\"]}', 'rule_fallback', 'FALLBACK', '2026-07-16 19:36:40.213398');
INSERT INTO `recommendation_sessions` VALUES ('a52369b6-c062-46ba-b083-016e2e8aa22a', 'student-001', '{\"goals\": \"希望学习人工智能与软件工程\", \"preferences\": [\"偏好实践课程\"]}', 'rule_fallback', 'FALLBACK', '2026-07-16 18:16:23.533310');
-- ----------------------------
-- Table structure for student_profiles
-- ----------------------------
DROP TABLE IF EXISTS `student_profiles`;
CREATE TABLE `student_profiles`  (
  `user_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_no` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `major` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `grade` int NOT NULL DEFAULT 1,
  PRIMARY KEY (`user_id`) USING BTREE,
  UNIQUE INDEX `uq_student_profiles_student_no`(`student_no` ASC) USING BTREE,
  CONSTRAINT `fk_student_profiles_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of student_profiles
-- ----------------------------
INSERT INTO `student_profiles` VALUES ('student-001', '2024001', 'Computer Science', 2);
INSERT INTO `student_profiles` VALUES ('student-002', '2024002', 'Mathematics', 2);
INSERT INTO `student_profiles` VALUES ('student-003', '2024003', 'Computer Science', 3);
-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_users_username`(`username` ASC) USING BTREE,
  INDEX `ix_users_role_status`(`role` ASC, `status` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of users
-- ----------------------------
INSERT INTO `users` VALUES ('academic-001', 'academic', 'sha256$c57fd13cbb1b1b4a7060d2557172607855220826b5b4167ea42017f919d4b085', 'ACADEMIC', 'ACTIVE');
INSERT INTO `users` VALUES ('student-001', 'student', 'sha256$703b0a3d6ad75b649a28adde7d83c6251da457549263bc7ff45ec709b0a8448b', 'STUDENT', 'ACTIVE');
INSERT INTO `users` VALUES ('student-002', 'student2', 'sha256$703b0a3d6ad75b649a28adde7d83c6251da457549263bc7ff45ec709b0a8448b', 'STUDENT', 'ACTIVE');
INSERT INTO `users` VALUES ('student-003', 'student3', 'sha256$703b0a3d6ad75b649a28adde7d83c6251da457549263bc7ff45ec709b0a8448b', 'STUDENT', 'ACTIVE');
-- ----------------------------
-- Table structure for waitlist_entries
-- ----------------------------
DROP TABLE IF EXISTS `waitlist_entries`;
CREATE TABLE `waitlist_entries`  (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `position` int NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `joined_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `skip_reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_waitlist_student_course`(`student_id` ASC, `course_id` ASC) USING BTREE,
  INDEX `ix_waitlist_course_order`(`course_id` ASC, `status` ASC, `joined_at` ASC, `id` ASC) USING BTREE,
  CONSTRAINT `fk_waitlist_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_waitlist_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
-- ----------------------------
-- Records of waitlist_entries
-- ----------------------------
INSERT INTO `waitlist_entries` VALUES ('waitlist-001', 'student-002', 'course-201', 1, 'WAITING', '2026-07-16 18:14:54.710796', NULL);
INSERT INTO `waitlist_entries` VALUES ('waitlist-002', 'student-003', 'course-201', 2, 'WAITING', '2026-07-16 18:14:54.710796', NULL);
SET FOREIGN_KEY_CHECKS = 1;
