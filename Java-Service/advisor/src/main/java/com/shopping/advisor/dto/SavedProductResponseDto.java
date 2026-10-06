package com.shopping.advisor.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class SavedProductResponseDto {
    private Long id;
    private String customTitle;
    private String imageUrl;
    private String sourceUrl;
    private BigDecimal price;
    private String note;
    private String categoryName;
    private Long categoryId;
    private LocalDateTime createdAt;
}