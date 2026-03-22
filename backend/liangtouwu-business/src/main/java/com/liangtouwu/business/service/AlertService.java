package com.liangtouwu.business.service;

import com.liangtouwu.domain.entity.Alert;
import java.util.List;

public interface AlertService {
    List<Alert> getAlerts(String search, String risk, String area);
}
