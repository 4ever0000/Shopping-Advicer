package com.shopping.advisor.controller;

import com.shopping.advisor.dto.SaveProductRequestDto;
import com.shopping.advisor.dto.SavedProductResponseDto;
import com.shopping.advisor.model.Category;
import com.shopping.advisor.service.SavedProductService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/saved-products")
@CrossOrigin(origins = "*") // Chrome Extension üçün CORS icazəsi
public class SavedProductController {

    private final SavedProductService savedProductService;

    public SavedProductController(SavedProductService savedProductService) {
        this.savedProductService = savedProductService;
    }

    // 1. Yeni məhsul yadda saxla (Kateqoriya yoxdursa avtomatik yaradır)
    @PostMapping
    public ResponseEntity<SavedProductResponseDto> saveProduct(@RequestBody SaveProductRequestDto dto) {
        return ResponseEntity.ok(savedProductService.saveProduct(dto));
    }

    // 2. Bütün kateqoriyaları gətir (Sol menuda dikey göstərmək üçün)
    @GetMapping("/categories")
    public ResponseEntity<List<Category>> getAllCategories() {
        return ResponseEntity.ok(savedProductService.getAllCategories());
    }

    // 3. Seçilmiş kateqoriyaya aid məhsulları gətir (Sağ tərəfdə listələmək üçün)
    @GetMapping("/category/{categoryId}")
    public ResponseEntity<List<SavedProductResponseDto>> getProductsByCategory(@PathVariable Long categoryId) {
        return ResponseEntity.ok(savedProductService.getProductsByCategory(categoryId));
    }

    // 4. Bütün yadda saxlanılan məhsulları gətir
    @GetMapping
    public ResponseEntity<List<SavedProductResponseDto>> getAllSavedProducts() {
        return ResponseEntity.ok(savedProductService.getAllSavedProducts());
    }

    // 5. Yadda saxlanılan məhsulu sil
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteSavedProduct(@PathVariable Long id) {
        savedProductService.deleteSavedProduct(id);
        return ResponseEntity.noContent().build();
    }
}