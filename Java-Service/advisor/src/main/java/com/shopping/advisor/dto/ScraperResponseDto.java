package com.shopping.advisor.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.io.Serializable; 
import java.util.List;
public record ScraperResponseDto(
   @JsonProperty("competitor_url") String competitorUrl,
    Double price,
    String currency,
    @JsonProperty("platform_name") String platformName,
    @JsonProperty("image_url") String imageUrl,
    List<String> comments
) implements Serializable {}