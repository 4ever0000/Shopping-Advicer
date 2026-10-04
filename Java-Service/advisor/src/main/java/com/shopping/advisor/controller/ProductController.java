package com.shopping.advisor.controller;

import com.shopping.advisor.dto.ProductRequestDto;
import com.shopping.advisor.dto.ProductResponseDto;
import com.shopping.advisor.dto.ScraperResponseDto;
import com.shopping.advisor.model.Product;
import com.shopping.advisor.repository.ProductRepository;
import com.shopping.advisor.service.ProductService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/products")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class ProductController {

    private final ProductRepository productRepository;
    private final ProductService productService;

    // 1. Bazadakı bütün məhsulları DTO şəklində gətirir
    @GetMapping
    public ResponseEntity<List<ProductResponseDto>> getAllProducts() {
        List<ProductResponseDto> responseDtos = productRepository.findAll().stream()
                .map(this::mapToResponseDto)
                .collect(Collectors.toList());
        return ResponseEntity.ok(responseDtos);
    }

    // 2. ID-yə görə tək məhsulu və onun rəqib qiymətlərini gətirir
    @GetMapping("/{id}")
    public ResponseEntity<ProductResponseDto> getProductById(@PathVariable Long id) {
        return productRepository.findById(id)
                .map(product -> ResponseEntity.ok(mapToResponseDto(product)))
                .orElse(ResponseEntity.notFound().build());
    }

    // 3. Əllə məhsul əlavə etmək üçün
    @PostMapping
    public ResponseEntity<ProductResponseDto> saveProduct(@RequestBody ProductRequestDto dto) {
        Product product = new Product();
        product.setProductName(dto.getProductName());
        product.setSourceUrl(dto.getSourceUrl());
        product.setInitialPrice(dto.getInitialPrice());
        product.setCurrency(dto.getCurrency());

        Product savedProduct = productRepository.save(product);
        return ResponseEntity.ok(mapToResponseDto(savedProduct));
    }

   
   // 4. PYTHON-U ÇAĞIRAN, REDİS KEŞİNDƏN VƏ YAXUD BAZADAN QAYTARAN ƏSAS ENDPOINT
    @PostMapping("/search")
    public ResponseEntity<ProductResponseDto> searchProduct(@RequestBody ProductRequestDto dto) {
        if (dto.getProductName() == null || dto.getProductName().trim().isEmpty()) {
            return ResponseEntity.badRequest().build();
        }
        
        // DƏYİŞİKLİK: dto.getProductName() əvəzinə bütün dto obyektini göndəririk
        ProductResponseDto responseDto = productService.searchAndSaveProduct(dto);
        return ResponseEntity.ok(responseDto);
    }

    // Helper method: JPA Product obyektini ProductResponseDto-ya çevirir
    private ProductResponseDto mapToResponseDto(Product product) {
    List<ScraperResponseDto> competitorDtos = (product.getCompetitorPrices() != null)
            ? product.getCompetitorPrices().stream()
                .map(cp -> new ScraperResponseDto(
                        cp.getCompetitorUrl(),
                        cp.getPrice(),
                        cp.getCurrency(),
                        cp.getPlatformName(),
                        cp.getImageUrl(),
                        cp.getComments()
                ))
                .collect(Collectors.toList())
            : Collections.emptyList();

    return new ProductResponseDto(
            product.getId(),
            product.getProductName(),
            product.getSourceUrl(),      // 3-cü parametr: String sourceUrl
            product.getInitialPrice(),   // 4-cü parametr: Double initialPrice
            product.getCurrency(),       // 5-ci parametr: String currency
            competitorDtos               // 6-cı parametr: List<ScraperResponseDto>
    );

    }
}