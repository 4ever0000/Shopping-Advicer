package com.shopping.advisor.dto;

import java.io.Serializable;
import java.util.List;

public record ProductResponseDto(
        Long id,
        String productName,
        String sourceUrl,
        Double initialPrice,
        String currency,
        List<ScraperResponseDto> competitorPrices
) implements Serializable {}