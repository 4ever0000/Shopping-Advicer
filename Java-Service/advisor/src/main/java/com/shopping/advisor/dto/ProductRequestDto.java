package com.shopping.advisor.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProductRequestDto {
    private String productName;

    @JsonProperty("current_url")
    private String currentUrl;
    
    private String sourceUrl;
    private Double initialPrice;
    private String currency;

    public ProductRequestDto(String productName) {
        this.productName = productName;
    }
}