package com.shopping.advisor.service;

import com.shopping.advisor.dto.ScraperResponseDto;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class ScraperClientService {

    private final RestTemplate restTemplate = new RestTemplate();
    private static final String PYTHON_SERVICE_URL = "http://python-service:8000/search";

    // Metod imzasını və requestBody hissəsini aşağıdakı kimi dəyişin:

    public List<ScraperResponseDto> getPricesFromScraper(String keyword, String currentUrl) {

        Map<String, String> requestBody = new HashMap<>();
        requestBody.put("product_name", keyword);
        requestBody.put("productName", keyword);
        requestBody.put("current_url", currentUrl != null ? currentUrl : ""); // Python-a ötürülür

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<Map<String, String>> entity = new HttpEntity<>(requestBody, headers);

        try {
            ResponseEntity<List<ScraperResponseDto>> response = restTemplate.exchange(
                    PYTHON_SERVICE_URL,
                    HttpMethod.POST,
                    entity,
                    new ParameterizedTypeReference<List<ScraperResponseDto>>() {
                    });
            return response.getBody();
        } catch (Exception e) {
            System.err.println("[ScraperClient] Python servisi ilə əlaqə xətası: " + e.getMessage());
            return List.of();
        }
    }
}