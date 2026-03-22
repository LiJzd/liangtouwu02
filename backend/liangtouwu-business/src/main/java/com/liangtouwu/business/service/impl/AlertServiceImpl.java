package com.liangtouwu.business.service.impl;

import com.liangtouwu.domain.entity.Alert;
import com.liangtouwu.business.mapper.AlertMapper;
import com.liangtouwu.business.service.AlertService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class AlertServiceImpl implements AlertService {
    @Autowired
    private AlertMapper alertMapper;

    @Override
    public List<Alert> getAlerts(String search, String risk, String area) {
        return alertMapper.findByCondition(search, risk, area);
    }
}
