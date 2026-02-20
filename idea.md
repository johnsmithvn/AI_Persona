# AI Core – Memory-First Personal Intelligence

## 1. Why This Exists

Tôi hay quên.

Tôi đọc một comment hay, lưu một repo thú vị,
viết một reflection sâu sắc.
Vài tuần sau, tôi không còn nhớ mình từng nghĩ gì.

Tôi không cần một chatbot chung chung.
Tôi cần một hệ thống có thể:

- Nhớ điều tôi từng viết
- Nhớ kỹ năng tôi từng đọc
- Nhớ note ghi chú của tôi
- Nhắc nhở tôi
- Trả lời dựa vào những gì tôi đã note
- Trò truyện như một bản thân thứ 2, một tư duy của mình training
- Nhớ cách tôi từng suy nghĩ
- So sánh tôi của hôm nay với tôi của 3 tháng trước
- Chỉ ra khi tôi tự mâu thuẫn

Dự án này tồn tại để trở thành “bộ não thứ hai”.

Không thay thế tôi.
Mà giúp tôi nhìn thấy chính mình rõ hơn.

Hệ thống này tấm gương có trí nhớ hoàn hảo.

Mỗi memory được thêm vào không chỉ là dữ liệu,
mà là một mảnh của thế giới quan đang được xây dựng.

Theo thời gian, hệ thống sẽ phản hồi theo pattern
được hình thành từ chính lịch sử tư duy của tôi.

Nó không trưởng thành độc lập.
Nó trưởng thành cùng tôi.

## 2. Core Philosophy

> Base model chỉ là cái não.  
> AI Core là cách cái não đó cư xử.

Hệ thống này không phải là một chatbot.
Nó là một lớp reasoning đặt trên một base model duy nhất.

Triết lý trung tâm:

- Memory là nền tảng.
- LLM không được sửa hoặc ghi trực tiếp vào memory.
- Reasoning phải dựa trên memory trước khi dựa vào kiến thức ngoài.
- Nếu không chắc → nói không chắc.
- Không bịa kiến thức.

Đây là Memory-First AI.
Không phải Prompt-Engineered Chatbot.

## 3. Memory Principles

### 3.1 Append-Only

Raw text là bất biến.

Memory không được chỉnh sửa.
Chỉ có thể thêm mới.

Điều này đảm bảo:

- REFLECT trung thực.
- CHALLENGE có thể dựa trên dữ liệu gốc.
- Không bóp méo quá khứ.

---

### 3.2 Context Decay (Sự phai mờ ký ức)

Không phải mọi memory đều bình đẳng.

Hệ thống phải:

- Nhận diện độ quan trọng (importance_score).
- Ưu tiên ký ức gần và quan trọng.
- Cho phép ký ức ít quan trọng mờ dần trong retrieval.

Memory tồn tại.
Nhưng không phải memory nào cũng được ưu tiên ngang nhau.

### 3.4 Selective Forgetting

Mặc dù raw text là bất biến,
hệ thống phải có khả năng:

- Archive hoặc soft-delete memory.
- Loại bỏ chúng khỏi lớp retrieval.
- Vẫn giữ lại trong storage nếu cần audit.

Quên không phải là xóa khỏi tồn tại.
Mà là loại khỏi lớp suy luận.

## 4. Epistemic Boundary

Hệ thống phải phân biệt rõ:

1. Reasoning dựa trên memory cá nhân.
2. Reasoning dựa trên kiến thức bên ngoài.

Nếu sử dụng kiến thức ngoài memory,
hệ thống phải thể hiện rõ điều đó.

Không được giả vờ rằng mọi suy luận đều xuất phát từ memory.

Minh bạch nguồn suy luận là bắt buộc.
## 5. Behavior Modes

Modes không phải là AI khác nhau.
Chỉ là cấu hình hành vi khác nhau.

### RECALL
- Trả nguyên văn memory.
- Không suy diễn.
- Không thêm kiến thức ngoài.

### REFLECT
- Tổng hợp nhiều memory.
- Nhận diện pattern và evolution.
- Có thể chỉ ra mâu thuẫn theo thời gian.

### CHALLENGE
- Phản biện dựa trên memory.
- Tìm inconsistency.
- Không tâng bốc.

---

### Citation Requirement

Bất kỳ mode nào sử dụng memory để suy luận
phải chỉ ra:

- Memory ID
hoặc
- Mốc thời gian

để người dùng có thể kiểm chứng.
## 6. Scope – Version 1

V1 tập trung vào:

- Single-user
- Text-based memory
- Semantic retrieval
- 3 mode: RECALL, REFLECT, CHALLENGE
- Logging cơ bản

Không làm:

- Multi-tenant
- Auth phức tạp
- Mobile app
- Auto mode classifier
- Streaming phức tạp
- Microservices

Giữ hệ thống nhỏ và sạch.

## 7. Long-Term Direction (Not V1)

Có thể phát triển thêm:

- Memory compression layer
- Re-embedding toàn bộ DB
- LoRA để khóa hành vi
- Tool integration
- Multi-user memory partition

Nhưng chỉ sau khi V1 ổn định
và triết lý không bị phá vỡ.

## 8. Final Statement

Đây không phải sản phẩm AI đại trà.

Đây là hệ thống giúp tôi:

- Nhìn rõ lịch sử tư duy của mình.
- Nhận diện sự thay đổi.
- Chấp nhận mâu thuẫn.
- Suy nghĩ sâu hơn.

Nếu hệ thống bắt đầu:
- Bịa,
- Che giấu mâu thuẫn,
- Hoặc làm mượt sự thật,

thì nó đã đi sai hướng.