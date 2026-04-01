import sys

target = '''        Alert alert = Alert.builder()
                .pigId(defaultValue(request.getPigId(), "UNKNOWN"))
                .area(defaultValue(request.getArea(), "未分区"))
                .type(defaultValue(request.getType(), "异常预警"))
                .risk(normalizeRisk(request.getRisk()))
                .timestamp(defaultValue(request.getTimestamp(), LocalDateTime.now().format(TIMESTAMP_FORMATTER)))
                .build();'''

repl = '''        Alert alert = Alert.builder()
                .pigId(defaultValue(request.getPigId(), "UNKNOWN"))
                .area(defaultValue(request.getArea(), "未分区"))
                .type(defaultValue(request.getType(), "异常预警"))
                .risk(normalizeRisk(request.getRisk()))
                .timestamp(defaultValue(request.getTimestamp(), LocalDateTime.now().format(TIMESTAMP_FORMATTER)))
                .build();
        
        alert.setMessage(buildAnnouncementText(alert, request.getAnnouncementText()));'''

with open('liangtouwu-business/src/main/java/com/liangtouwu/business/service/impl/AlertServiceImpl.java', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(target, repl)

with open('liangtouwu-business/src/main/java/com/liangtouwu/business/service/impl/AlertServiceImpl.java', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated AlertServiceImpl.java')
