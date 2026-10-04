package com.shopping.advisor.service;

import com.shopping.advisor.dto.ProductRequestDto;
import com.shopping.advisor.dto.ProductResponseDto;
import com.shopping.advisor.dto.ScraperResponseDto;
import com.shopping.advisor.model.CompetitorPrice;
import com.shopping.advisor.model.Product;
import com.shopping.advisor.repository.CompetitorPriceRepository;
import com.shopping.advisor.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Service
@RequiredArgsConstructor
public class ProductService {

    private final ScraperClientService scraperClientService;
    private final ProductRepository productRepository;
    private final CompetitorPriceRepository competitorPriceRepository;
    private final CurrencyService currencyService;

    @Cacheable(value = "products", key = "#requestDto.productName")
    @Transactional
    public ProductResponseDto searchAndSaveProduct(ProductRequestDto requestDto) {
        if (requestDto == null || requestDto.getProductName() == null) {
            return new ProductResponseDto(null, "", null, 0.0, "AZN", Collections.emptyList());
        }

        String cleanKeyword = requestDto.getProductName().trim();
        String currentUrl = requestDto.getCurrentUrl();

        // 1. Python-dan canlı məlumatı çəkirik (currentUrl parametrini də ötürürük)
        List<ScraperResponseDto> scrapedDataList = Collections.emptyList();
        try {
            scrapedDataList = scraperClientService.getPricesFromScraper(cleanKeyword, currentUrl);
        } catch (Exception e) {
            System.err.println("Scraper service error: " + e.getMessage());
        }

        Product product = productRepository.findByProductName(cleanKeyword)
                .orElseGet(() -> {
                    Product newProduct = new Product();
                    newProduct.setProductName(cleanKeyword);
                    return productRepository.save(newProduct);
                });

        // KÖHNƏ XƏTALI QİYMƏTLƏRİ BAZADAN TƏMİZLƏYİRİK
        if (product.getCompetitorPrices() != null && !product.getCompetitorPrices().isEmpty()) {
            competitorPriceRepository.deleteAll(product.getCompetitorPrices());
            product.getCompetitorPrices().clear();
        }

        Double minPrice = Double.MAX_VALUE;
        String cheapestUrl = null;
        List<ScraperResponseDto> resultDtoList = new ArrayList<>();

        for (ScraperResponseDto data : scrapedDataList) {
            if (data != null && data.price() != null && data.price() > 0) {
                Double finalPrice = data.price();
                String finalCurrency = data.currency();

                if ("TRY".equalsIgnoreCase(finalCurrency)) {
                    finalPrice = currencyService.convertTryToAzn(data.price());
                    finalCurrency = "AZN";
                } else if ("USD".equalsIgnoreCase(finalCurrency)) {
                    // 1 USD = 1.70 AZN məzənnəsi ilə avtomatik çeviririk
                    finalPrice = Math.round((data.price() * 1.70) * 100.0) / 100.0;
                    finalCurrency = "AZN";
                }

                if (finalPrice < minPrice) {
                    minPrice = finalPrice;
                    cheapestUrl = data.competitorUrl();
                }

                String platformName = (data.platformName() != null && !data.platformName().isEmpty())
                        ? data.platformName()
                        : "Unknown";

                // Boş və ya null rəyləri təmizləyirik
                List<String> safeComments = new ArrayList<>();
                if (data.comments() != null) {
                    for (String comment : data.comments()) {
                        if (comment != null && !comment.trim().isEmpty()) {
                            safeComments.add(comment.trim());
                        }
                    }
                }

                CompetitorPrice priceEntry = new CompetitorPrice();
                priceEntry.setPrice(finalPrice);
                priceEntry.setCompetitorUrl(data.competitorUrl());
                priceEntry.setCurrency(finalCurrency);
                priceEntry.setImageUrl(data.imageUrl());
                priceEntry.setComments(safeComments);
                priceEntry.setPlatformName(platformName);
                priceEntry.setProduct(product);

                competitorPriceRepository.save(priceEntry);

                resultDtoList.add(new ScraperResponseDto(
                        data.competitorUrl(),
                        finalPrice,
                        finalCurrency,
                        platformName,
                        data.imageUrl(),
                        safeComments));
            }
        }

        // Əgər qiymət tapılıbsa yeniləyirik, tapılmayıbsa köhnə məlumatları
        // sıfırlayırıq
        if (minPrice != Double.MAX_VALUE) {
            product.setInitialPrice(minPrice);
            product.setSourceUrl(cheapestUrl);
            product.setCurrency("AZN");
        } else {
            product.setInitialPrice(null);
            product.setSourceUrl(null);
            product.setCurrency(null);
        }
        productRepository.save(product);

        return new ProductResponseDto(
                product.getId(),
                product.getProductName(),
                cheapestUrl,
                (minPrice == Double.MAX_VALUE) ? 0.0 : minPrice,
                "AZN",
                resultDtoList);
    }
}