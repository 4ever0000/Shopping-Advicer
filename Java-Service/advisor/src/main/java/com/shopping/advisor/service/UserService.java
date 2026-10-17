package com.shopping.advisor.service;

import com.shopping.advisor.dto.AuthResponseDto;
import com.shopping.advisor.dto.LoginRequestDto;
import com.shopping.advisor.dto.RegisterRequestDto;
import com.shopping.advisor.model.User;
import com.shopping.advisor.repository.UserRepository;
import com.shopping.advisor.security.JwtUtil;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final BCryptPasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    public UserService(UserRepository userRepository, JwtUtil jwtUtil) {
        this.userRepository = userRepository;
        this.passwordEncoder = new BCryptPasswordEncoder();
        this.jwtUtil = jwtUtil;
    }

    public AuthResponseDto register(RegisterRequestDto dto) {
        if (userRepository.existsByEmailIgnoreCase(dto.getEmail())) {
            throw new RuntimeException("Bu e-poçt ünvanı artıq istifadə olunur!");
        }

        User user = new User();
        user.setFullName(dto.getFullName());
        user.setEmail(dto.getEmail().toLowerCase().trim());
        user.setPassword(passwordEncoder.encode(dto.getPassword())); // BCrypt ilə şifrələmə

        userRepository.save(user);

        String token = jwtUtil.generateToken(user.getEmail());
        return new AuthResponseDto(token, user.getEmail(), user.getFullName());
    }

    public AuthResponseDto login(LoginRequestDto dto) {
        User user = userRepository.findByEmailIgnoreCase(dto.getEmail())
                .orElseThrow(() -> new RuntimeException("E-poçt və ya şifrə yanlışdır!"));

        if (!passwordEncoder.matches(dto.getPassword(), user.getPassword())) {
            throw new RuntimeException("E-poçt və ya şifrə yanlışdır!");
        }

        String token = jwtUtil.generateToken(user.getEmail());
        return new AuthResponseDto(token, user.getEmail(), user.getFullName());
    }
}