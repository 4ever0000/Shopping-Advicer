package com.shopping.advisor.service;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import java.util.Map;
import java.time.LocalDateTime;

@Service
public class CurrencyService {

    private final RestTemplate restTemplate = new RestTemplate();
    
    // Məzənnəni və son yenilənmə vaxtını yaddaşda saxlayacaq dəyişənlər
    private Double cachedTryToAznRate = null;
    private LocalDateTime lastFetchTime = null;

    // Açıq və pulsuz Exchange Rate API
    private static final String API_URL = "https://open.er-api.com/v6/latest/TRY";

    /**
     * TRY məbləğini AZN-ə çevirir.
     */
    public Double convertTryToAzn(Double tryAmount) {
        if (tryAmount == null || tryAmount <= 0) {
            return 0.0;
        }

        Double rate = getTryToAznRate();
        double converted = tryAmount * rate;

        // Yuvarlaqlaşdırma: Vergüldən sonra 2 rəqəm saxlayırıq
        return Math.round(converted * 100.0) / 100.0;
    }

    /**
     * TRY -> AZN Məzənnəsini qaytarır.
     * Əgər yaddaşdakı məlumat 1 saatdan köhnədirsə, API-yə müraciət edib yeniləyir.
     */
    @SuppressWarnings("unchecked")
    public synchronized Double getTryToAznRate() {
        boolean isExpired = lastFetchTime == null || lastFetchTime.isBefore(LocalDateTime.now().minusHours(1));

        if (cachedTryToAznRate == null || isExpired) {
            try {
                // API-dən məzənnə məlumatlarını çəkirik
                Map<String, Object> response = restTemplate.getForObject(API_URL, Map.class);

                if (response != null && response.containsKey("rates")) {
                    Map<String, Object> rates = (Map<String, Object>) response.get("rates");
                    if (rates.containsKey("AZN")) {
                        Object aznRateObj = rates.get("AZN");
                        cachedTryToAznRate = Double.parseDouble(aznRateObj.toString());
                        lastFetchTime = LocalDateTime.now();
                        System.out.println("[CURRENCY SERVICE] Yeni məzənnə API-dən alındı: 1 TRY = " + cachedTryToAznRate + " AZN");
                    }
                }
            } catch (Exception e) {
                System.err.println("[CURRENCY SERVICE XƏTASI] Məzənnə çəkilə bilmədi: " + e.getMessage());
                // API xətası olarsa, tətbiqin çökməməsi üçün ehtiyat (fallback) məzənnə istifadə olunur
                if (cachedTryToAznRate == null) {
                    cachedTryToAznRate = 0.05; // Fallback rate
                }
            }
        }

        return cachedTryToAznRate;
    }
}