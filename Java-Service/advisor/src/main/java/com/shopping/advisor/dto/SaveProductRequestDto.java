package com.shopping.advisor.dto;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class SaveProductRequestDto {
    private String customTitle;
    private String imageUrl;
    private String sourceUrl;
    private BigDecimal price;
    private String note;
    private String categoryName;
}