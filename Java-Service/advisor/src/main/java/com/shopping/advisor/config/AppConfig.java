package com.shopping.advisor.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class AppConfig {

    @Bean
    public RestClient scraperRestClient() {
        return RestClient.builder()
                .baseUrl("http://localhost:8000")
                .build();
    }
}
