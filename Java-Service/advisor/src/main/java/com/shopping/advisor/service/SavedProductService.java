package com.shopping.advisor.service;

import com.shopping.advisor.dto.SaveProductRequestDto;
import com.shopping.advisor.dto.SavedProductResponseDto;
import com.shopping.advisor.model.Category;
import com.shopping.advisor.model.SavedProduct;
import com.shopping.advisor.repository.CategoryRepository;
import com.shopping.advisor.repository.SavedProductRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class SavedProductService {

    private final SavedProductRepository savedProductRepository;
    private final CategoryRepository categoryRepository;

    public SavedProductService(SavedProductRepository savedProductRepository, CategoryRepository categoryRepository) {
        this.savedProductRepository = savedProductRepository;
        this.categoryRepository = categoryRepository;
    }

    @Transactional
    public SavedProductResponseDto saveProduct(SaveProductRequestDto dto) {
        String catName = (dto.getCategoryName() == null || dto.getCategoryName().isBlank()) 
                ? "Ümumi" 
                : dto.getCategoryName().trim();

        Category category = categoryRepository.findByNameIgnoreCase(catName)
                .orElseGet(() -> categoryRepository.save(new Category(catName)));

        SavedProduct product = new SavedProduct();
        product.setCustomTitle(dto.getCustomTitle());
        product.setImageUrl(dto.getImageUrl());
        product.setSourceUrl(dto.getSourceUrl());
        product.setPrice(dto.getPrice());
        product.setNote(dto.getNote());
        product.setCategory(category);

        SavedProduct saved = savedProductRepository.save(product);
        return mapToDto(saved);
    }

    public List<Category> getAllCategories() {
        return categoryRepository.findAll();
    }

    public List<SavedProductResponseDto> getProductsByCategory(Long categoryId) {
        return savedProductRepository.findByCategoryId(categoryId)
                .stream().map(this::mapToDto).collect(Collectors.toList());
    }

    public List<SavedProductResponseDto> getAllSavedProducts() {
        return savedProductRepository.findAll()
                .stream().map(this::mapToDto).collect(Collectors.toList());
    }

    @Transactional
    public void deleteSavedProduct(Long id) {
        savedProductRepository.deleteById(id);
    }

    private SavedProductResponseDto mapToDto(SavedProduct product) {
        SavedProductResponseDto dto = new SavedProductResponseDto();
        dto.setId(product.getId());
        dto.setCustomTitle(product.getCustomTitle());
        dto.setImageUrl(product.getImageUrl());
        dto.setSourceUrl(product.getSourceUrl());
        dto.setPrice(product.getPrice());
        dto.setNote(product.getNote());
        dto.setCreatedAt(product.getCreatedAt());
        if (product.getCategory() != null) {
            dto.setCategoryName(product.getCategory().getName());
            dto.setCategoryId(product.getCategory().getId());
        }
        return dto;
    }
}