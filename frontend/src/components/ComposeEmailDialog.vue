<template>
  <div v-if="isDialogOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-black bg-opacity-50" @click="closeDialog"></div>

    <!-- Dialog -->
    <div class="relative bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Compose Email</h2>
        <button @click="closeDialog" class="text-gray-400 hover:text-gray-600">
          <FeatherIcon name="x" class="w-5 h-5" />
        </button>
      </div>

      <!-- Content -->
      <div class="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
        <div class="space-y-6">
          <!-- Recipients Section -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Recipients <span class="text-red-500">*</span></label>
            <div class="flex items-start space-x-2">
              <div class="flex-1">
                <!-- Recipients Pills Container -->
                <div class="w-full min-h-[80px] px-3 py-2 border border-gray-300 rounded-md focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500">
                  <div class="flex flex-wrap gap-2 mb-2">
                    <!-- Group Pills -->
                    <div
                      v-for="group in selectedGroups"
                      :key="'group-' + group.name"
                      class="relative group"
                    >
                      <div
                        class="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm cursor-pointer hover:bg-blue-200 transition-colors"
                        @click="toggleGroupExpansion(group.name)"
                      >
                        <FeatherIcon name="users" class="w-3 h-3" />
                        <span class="font-medium">{{ group.title || group.name }}</span>
                        <span class="text-xs text-blue-600">({{ group.email_count || 0 }})</span>
                        <button
                          type="button"
                          @click.stop="removeGroup(group.name)"
                          class="ml-1 hover:bg-blue-300 rounded-full p-0.5"
                        >
                          <FeatherIcon name="x" class="w-3 h-3" />
                        </button>
                      </div>

                      <!-- Expanded Group Members -->
                      <div
                        v-if="expandedGroups.includes(group.name)"
                        class="absolute z-20 mt-1 p-3 bg-white border border-gray-300 rounded-lg shadow-lg max-w-xs"
                      >
                        <div class="flex items-center justify-between mb-2">
                          <h4 class="text-sm font-semibold text-gray-700">{{ group.title || group.name }} Members</h4>
                          <button
                            type="button"
                            @click="toggleGroupExpansion(group.name)"
                            class="text-gray-400 hover:text-gray-600"
                          >
                            <FeatherIcon name="x" class="w-4 h-4" />
                          </button>
                        </div>
                        <div class="max-h-40 overflow-y-auto space-y-1">
                          <div
                            v-for="(email, idx) in (group.emails || [])"
                            :key="idx"
                            class="text-xs text-gray-600 py-1 px-2 bg-gray-50 rounded"
                          >
                            {{ email }}
                          </div>
                          <div v-if="!group.emails || group.emails.length === 0" class="text-xs text-gray-400 italic">
                            No members loaded
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Individual Email Pills -->
                    <div
                      v-for="(email, index) in emailPills"
                      :key="'email-' + index"
                      :class="[
                        'inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm relative group',
                        email.status === 'valid' ? 'bg-green-100 text-green-800' :
                        email.status === 'invalid' ? 'bg-red-100 text-red-800' :
                        email.status === 'duplicate' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'
                      ]"
                      :title="email.reason || ''"
                    >
                      <!-- Status Icon -->
                      <span v-if="email.status === 'invalid'" class="text-red-600">⚠️</span>
                      <span v-if="email.status === 'duplicate'" class="text-yellow-600">⚠</span>
                      <span v-if="email.status === 'valid'" class="text-green-600">✓</span>

                      <span>{{ email.address }}</span>
                      <button
                        type="button"
                        @click="removeEmailPill(index)"
                        :class="[
                          'hover:bg-opacity-50 rounded-full p-0.5',
                          email.status === 'valid' ? 'hover:bg-green-300' :
                          email.status === 'invalid' ? 'hover:bg-red-300' :
                          email.status === 'duplicate' ? 'hover:bg-yellow-300' : 'hover:bg-gray-300'
                        ]"
                      >
                        <FeatherIcon name="x" class="w-3 h-3" />
                      </button>

                      <!-- Enhanced Tooltip -->
                      <div
                        v-if="email.reason"
                        class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 text-xs text-white rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 whitespace-nowrap z-30"
                        :class="[
                          email.status === 'invalid' ? 'bg-red-600' :
                          email.status === 'duplicate' ? 'bg-yellow-600' : 'bg-gray-600'
                        ]"
                      >
                        {{ email.reason }}
                        <!-- Tooltip Arrow -->
                        <div
                          class="absolute top-full left-1/2 -translate-x-1/2 -mt-1 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent"
                          :class="[
                            email.status === 'invalid' ? 'border-t-red-600' :
                            email.status === 'duplicate' ? 'border-t-yellow-600' : 'border-t-gray-600'
                          ]"
                        ></div>
                      </div>
                    </div>
                  </div>

                  <!-- Input Field -->
                  <input
                    ref="recipientInput"
                    v-model="currentEmailInput"
                    @keydown="handleEmailInputKeydown"
                    @paste="handleEmailPaste"
                    @blur="handleEmailInputBlur"
                    type="text"
                    placeholder="Type email and press comma or enter..."
                    class="w-full outline-none text-sm"
                  />
                </div>
              </div>
              <Button
                @click="showGroupSelector = true"
                variant="outline"
                size="sm"
                class="mt-1"
              >
                <template #prefix>
                  <FeatherIcon name="users" class="w-4 h-4" />
                </template>
                Select Group
              </Button>
            </div>
            <p class="text-xs text-gray-500 mt-1">
              Total Recipients: {{ totalRecipientCount }} ({{ validEmailCount }} valid, {{ invalidEmailCount }} invalid, {{ duplicateEmailCount }} duplicates)
            </p>
          </div>

          <!-- Subject -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Subject <span class="text-red-500">*</span></label>
            <input
              v-model="formData.subject"
              type="text"
              placeholder="Enter email subject"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <!-- Content Type Selection -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Content Type</label>
            <select
              v-model="formData.content_type"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="Rich Text">Rich Text</option>
              <option value="Markdown">Markdown</option>
              <option value="HTML">HTML</option>
            </select>
          </div>

          <!-- Message Content -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Message <span class="text-red-500">*</span></label>

            <!-- Rich Text Editor -->
            <div v-if="formData.content_type === 'Rich Text'" class="border border-gray-300 rounded-lg overflow-hidden">
              <!-- Tiptap Toolbar -->
              <div v-if="editor" class="bg-gray-50 p-2 border-b border-gray-300">
                <!-- Row 1: Text Formatting -->
                <div class="flex flex-wrap gap-1 mb-2">
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleBold().run()"
                    :class="{ 'bg-gray-200': editor.isActive('bold') }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 font-bold"
                    title="Bold (Ctrl+B)"
                  >
                    B
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleItalic().run()"
                    :class="{ 'bg-gray-200': editor.isActive('italic') }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 italic"
                    title="Italic (Ctrl+I)"
                  >
                    I
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleUnderline().run()"
                    :class="{ 'bg-gray-200': editor.isActive('underline') }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 underline"
                    title="Underline (Ctrl+U)"
                  >
                    U
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleStrike().run()"
                    :class="{ 'bg-gray-200': editor.isActive('strike') }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 line-through"
                    title="Strikethrough"
                  >
                    S
                  </button>

                  <div class="border-l border-gray-300 mx-1"></div>

                  <!-- Color Picker -->
                  <div class="relative inline-block">
                    <button
                      type="button"
                      @click="showTextColorPicker = !showTextColorPicker"
                      class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 flex items-center gap-1"
                      title="Text Color"
                    >
                      A
                      <span class="w-4 h-1 bg-current"></span>
                    </button>
                    <div v-if="showTextColorPicker" class="absolute z-10 mt-1 p-2 bg-white border border-gray-300 rounded shadow-lg">
                      <input
                        type="color"
                        v-model="textColor"
                        @change="applyTextColor(textColor)"
                        class="w-20 h-8"
                      />
                      <button
                        @click="editor.chain().focus().unsetColor().run(); showTextColorPicker = false"
                        class="mt-1 px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200 w-full"
                      >
                        Clear
                      </button>
                    </div>
                  </div>

                  <!-- Highlight Color -->
                  <div class="relative inline-block">
                    <button
                      type="button"
                      @click="showHighlightColorPicker = !showHighlightColorPicker"
                      :class="{ 'bg-gray-200': editor.isActive('highlight') }"
                      class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                      title="Highlight"
                    >
                      🎨
                    </button>
                    <div v-if="showHighlightColorPicker" class="absolute z-10 mt-1 p-2 bg-white border border-gray-300 rounded shadow-lg">
                      <input
                        type="color"
                        v-model="highlightColor"
                        @change="applyHighlight(highlightColor)"
                        class="w-20 h-8"
                      />
                      <button
                        @click="editor.chain().focus().unsetHighlight().run(); showHighlightColorPicker = false"
                        class="mt-1 px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200 w-full"
                      >
                        Clear
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Row 2: Headings & Alignment -->
                <div class="flex flex-wrap gap-1 mb-2">
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleHeading({ level: 1 }).run()"
                    :class="{ 'bg-gray-200': editor.isActive('heading', { level: 1 }) }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 font-bold"
                    title="Heading 1"
                  >
                    H1
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
                    :class="{ 'bg-gray-200': editor.isActive('heading', { level: 2 }) }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 font-bold"
                    title="Heading 2"
                  >
                    H2
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleHeading({ level: 3 }).run()"
                    :class="{ 'bg-gray-200': editor.isActive('heading', { level: 3 }) }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 font-bold"
                    title="Heading 3"
                  >
                    H3
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().setParagraph().run()"
                    :class="{ 'bg-gray-200': editor.isActive('paragraph') }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Paragraph"
                  >
                    P
                  </button>

                  <div class="border-l border-gray-300 mx-1"></div>

                  <!-- Text Alignment -->
                  <button
                    type="button"
                    @click="editor.chain().focus().setTextAlign('left').run()"
                    :class="{ 'bg-gray-200': editor.isActive({ textAlign: 'left' }) }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Align Left"
                  >
                    ⫷
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().setTextAlign('center').run()"
                    :class="{ 'bg-gray-200': editor.isActive({ textAlign: 'center' }) }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Align Center"
                  >
                    ≡
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().setTextAlign('right').run()"
                    :class="{ 'bg-gray-200': editor.isActive({ textAlign: 'right' }) }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Align Right"
                  >
                    ⫸
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().setTextAlign('justify').run()"
                    :class="{ 'bg-gray-200': editor.isActive({ textAlign: 'justify' }) }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Justify"
                  >
                    ▤
                  </button>
                </div>

                <!-- Row 3: Lists, Images & Tables -->
                <div class="flex flex-wrap gap-1">
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleBulletList().run()"
                    :class="{ 'bg-gray-200': editor.isActive('bulletList') }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Bullet List"
                  >
                    •
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleOrderedList().run()"
                    :class="{ 'bg-gray-200': editor.isActive('orderedList') }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Numbered List"
                  >
                    1.
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleBlockquote().run()"
                    :class="{ 'bg-gray-200': editor.isActive('blockquote') }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Quote"
                  >
                    "
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().toggleCodeBlock().run()"
                    :class="{ 'bg-gray-200': editor.isActive('codeBlock') }"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 font-mono"
                    title="Code Block"
                  >
                    &lt;/&gt;
                  </button>

                  <div class="border-l border-gray-300 mx-1"></div>

                  <!-- Image Upload -->
                  <button
                    type="button"
                    @click="$refs.imageInput.click()"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Upload Image"
                  >
                    📷
                  </button>
                  <input
                    ref="imageInput"
                    type="file"
                    accept="image/*"
                    @change="uploadImage"
                    class="hidden"
                  />
                  <button
                    type="button"
                    @click="addImage"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Insert Image URL"
                  >
                    🖼️
                  </button>

                  <!-- Table -->
                  <button
                    type="button"
                    @click="insertTable"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Insert Table"
                  >
                    ⊞
                  </button>

                  <div class="border-l border-gray-300 mx-1"></div>

                  <button
                    type="button"
                    @click="editor.chain().focus().setHorizontalRule().run()"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100"
                    title="Horizontal Line"
                  >
                    —
                  </button>

                  <div class="border-l border-gray-300 mx-1"></div>

                  <button
                    type="button"
                    @click="editor.chain().focus().undo().run()"
                    :disabled="!editor.can().undo()"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Undo"
                  >
                    ↶
                  </button>
                  <button
                    type="button"
                    @click="editor.chain().focus().redo().run()"
                    :disabled="!editor.can().redo()"
                    class="px-3 py-1 text-sm border border-gray-200 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Redo"
                  >
                    ↷
                  </button>
                </div>
              </div>

              <!-- Tiptap Content Area -->
              <EditorContent :editor="editor" class="tiptap-editor" />
            </div>

            <!-- Markdown Editor -->
            <div v-else-if="formData.content_type === 'Markdown'">
              <textarea
                v-model="formData.message_md"
                placeholder="Compose your email message in Markdown..."
                rows="10"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
              ></textarea>
            </div>

            <!-- HTML Editor -->
            <div v-else-if="formData.content_type === 'HTML'">
              <textarea
                v-model="formData.message_html"
                placeholder="Compose your email message in HTML..."
                rows="10"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
              ></textarea>
            </div>
          </div>

          <!-- Attachments Section -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Attachments</label>
            <div class="border border-gray-300 rounded-lg p-4 bg-gray-50">
              <!-- Attachment Pills -->
              <div v-if="attachments.length > 0" class="flex flex-wrap gap-2 mb-3">
                <div
                  v-for="(file, index) in attachments"
                  :key="'attachment-' + index"
                  class="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm hover:bg-gray-50 transition-colors"
                >
                  <!-- File Icon -->
                  <div class="flex-shrink-0">
                    <svg v-if="isImageFile(file)" class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <svg v-else-if="isPDFFile(file)" class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    <svg v-else class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>

                  <!-- File Info -->
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-gray-900 truncate">{{ file.name }}</div>
                    <div class="text-xs text-gray-500">{{ formatFileSize(file.size) }}</div>
                  </div>

                  <!-- Remove Button -->
                  <button
                    type="button"
                    @click="removeAttachment(index)"
                    class="flex-shrink-0 text-gray-400 hover:text-red-600 transition-colors"
                    title="Remove attachment"
                  >
                    <FeatherIcon name="x" class="w-4 h-4" />
                  </button>
                </div>
              </div>

              <!-- Upload Button -->
              <div class="flex items-center gap-2">
                <input
                  ref="attachmentInput"
                  type="file"
                  multiple
                  @change="handleFileAttachment"
                  class="hidden"
                />
                <Button
                  @click="$refs.attachmentInput.click()"
                  variant="outline"
                  size="sm"
                >
                  <template #prefix>
                    <FeatherIcon name="paperclip" class="w-4 h-4" />
                  </template>
                  Add Attachments
                </Button>
                <span v-if="attachments.length > 0" class="text-xs text-gray-500">
                  {{ attachments.length }} file{{ attachments.length !== 1 ? 's' : '' }} ({{ formatFileSize(totalAttachmentSize) }})
                </span>
              </div>

              <!-- Max Size Warning -->
              <p class="text-xs text-gray-500 mt-2">
                Maximum file size: 10MB per file. Supported formats: All common file types.
              </p>
            </div>
          </div>

          <!-- Email Options -->
          <div class="bg-gray-50 p-4 rounded-lg">
            <h3 class="text-sm font-medium text-gray-700 mb-3">Email Options</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="space-y-3">
                <label class="flex items-center">
                  <input type="checkbox" v-model="formData.send_unsubscribe_link" class="mr-2" />
                  <span class="text-sm text-gray-700">Send Unsubscribe Link</span>
                </label>
                <!-- <label class="flex items-center">
                  <input type="checkbox" v-model="formData.send_webview_link" class="mr-2" />
                  <span class="text-sm text-gray-700">Send Web View Link</span>
                </label> -->
                <!-- <label class="flex items-center">
                  <input type="checkbox" v-model="formData.published" class="mr-2" />
                  <span class="text-sm text-gray-700">Publish as Web Page</span>
                </label> -->
              </div>
              <div class="space-y-3">
                <label class="flex items-center">
                  <input type="checkbox" v-model="sendLater" class="mr-2" />
                  <span class="text-sm text-gray-700">Schedule sending at a later time</span>
                </label>
                <div v-if="sendLater">
                  <label class="block text-sm font-medium text-gray-700 mb-1">Send Email At</label>
                  <input
                    v-model="formData.schedule_send"
                    type="datetime-local"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Campaign and Route -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Campaign (Optional)</label>
              <input
                v-model="formData.campaign"
                type="text"
                placeholder="Enter campaign name"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div v-if="formData.published">
              <label class="block text-sm font-medium text-gray-700 mb-1">Route</label>
              <input
                v-model="formData.route"
                type="text"
                placeholder="e.g., newsletter/my-newsletter"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
        <Button @click="closeDialog" variant="outline">
          Cancel
        </Button>
        <div class="flex items-center space-x-3">
          <Button @click="saveDraft" variant="outline" :loading="isSaving">
            <template #prefix>
              <FeatherIcon name="save" class="w-4 h-4" />
            </template>
            Save Draft
          </Button>
          <Button @click="sendEmail" variant="solid" :loading="isSubmitting">
            {{ sendLater ? 'Schedule Email' : 'Send Email' }}
          </Button>
        </div>
      </div>
    </div>
  </div>

  <!-- Group Selector Dialog -->
  <GroupSelectorDialog
    v-model:show="showGroupSelector"
    @groups-selected="handleGroupsSelected"
  />

  <!-- Group Naming Dialog -->
  <div v-if="showGroupNamingDialog" class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-black bg-opacity-50" @click="cancelGroupNaming"></div>

    <!-- Dialog -->
    <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Save Email Group</h2>
        <button @click="cancelGroupNaming" class="text-gray-400 hover:text-gray-600">
          <FeatherIcon name="x" class="w-5 h-5" />
        </button>
      </div>

      <!-- Content -->
      <div class="p-6">
        <p class="text-sm text-gray-600 mb-4">
          {{ groupNamingMessage }}
        </p>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Group Name (Optional)
          </label>
          <input
            ref="groupNameInput"
            v-model="newGroupName"
            type="text"
            placeholder="e.g., Marketing Team"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            @keydown.enter="confirmGroupNaming"
          />
          <p class="text-xs text-gray-500 mt-1">
            Leave empty to create a temporary group
          </p>
        </div>

        <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <h4 class="text-sm font-medium text-blue-900 mb-2">Recipients to be saved:</h4>
          <div class="text-xs text-blue-800 space-y-1 max-h-32 overflow-y-auto">
            <div v-for="email in pendingGroupEmails" :key="email" class="py-1">
              {{ email }}
            </div>
          </div>
          <div class="mt-2 pt-2 border-t border-blue-200 text-sm font-medium text-blue-900">
            Total: {{ pendingGroupEmails.length }} recipients
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 bg-gray-50">
        <Button @click="cancelGroupNaming" variant="outline">
          Cancel
        </Button>
        <Button @click="skipGroupNaming" variant="outline">
          Skip (Create Temporary)
        </Button>
        <Button @click="confirmGroupNaming" variant="solid">
          {{ newGroupName ? 'Save Group' : 'Continue' }}
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineEmits, defineProps, onMounted, onBeforeUnmount } from 'vue'
import { Button, FeatherIcon, createResource, call } from 'frappe-ui'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import ResizableImageExtension from 'tiptap-extension-resize-image'
import TextAlign from '@tiptap/extension-text-align'
import TextStyle from '@tiptap/extension-text-style'
import Color from '@tiptap/extension-color'
import FontFamily from '@tiptap/extension-font-family'
import Highlight from '@tiptap/extension-highlight'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableHeader from '@tiptap/extension-table-header'
import TableCell from '@tiptap/extension-table-cell'
import GroupSelectorDialog from './GroupSelectorDialog.vue'
import { session } from '../data/session'

// Props
const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['update:show', 'email-sent'])

// Dialog state
const isDialogOpen = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
})

// Form state
const isSubmitting = ref(false)
const isSaving = ref(false)
const showGroupSelector = ref(false)
const sendLater = ref(false)

// Group naming dialog state
const showGroupNamingDialog = ref(false)
const newGroupName = ref('')
const groupNameInput = ref(null)
const pendingGroupEmails = ref([])
const groupNamingMessage = ref('')
const groupNamingCallback = ref(null)

// Tiptap Editor
const editor = useEditor({
  extensions: [
    StarterKit,
    Underline,
    ResizableImageExtension.configure({
      inline: true,
      allowBase64: true,
    }),
    TextAlign.configure({
      types: ['heading', 'paragraph'],
    }),
    TextStyle,
    Color,
    FontFamily,
    Highlight.configure({
      multicolor: true,
    }),
    Table.configure({
      resizable: true,
    }),
    TableRow,
    TableHeader,
    TableCell,
  ],
  content: '',
  editorProps: {
    attributes: {
      class: 'w-full px-3 py-2 focus:outline-none min-h-[200px] max-h-[400px] overflow-y-auto prose prose-sm max-w-none',
    },
  },
  onUpdate: ({ editor }) => {
    formData.value.message = editor.getHTML()
  },
})

// Image upload handler
const imageInput = ref(null)
const addImage = () => {
  const url = prompt('Enter image URL (or paste base64 data URI):')
  if (url) {
    editor.value.chain().focus().setImage({ src: url }).run()
  }
}

const uploadImage = (event) => {
  const file = event.target.files[0]
  if (file && file.type.startsWith('image/')) {
    const reader = new FileReader()
    reader.onload = (e) => {
      editor.value.chain().focus().setImage({ src: e.target.result }).run()
    }
    reader.readAsDataURL(file)
  }
}

// Color picker refs
const showTextColorPicker = ref(false)
const showHighlightColorPicker = ref(false)
const textColor = ref('#000000')
const highlightColor = ref('#ffff00')

const applyTextColor = (color) => {
  editor.value.chain().focus().setColor(color).run()
  showTextColorPicker.value = false
}

const applyHighlight = (color) => {
  editor.value.chain().focus().toggleHighlight({ color }).run()
  showHighlightColorPicker.value = false
}

const applyFontSize = () => {
  const size = prompt('Enter font size (e.g., 16px, 1.5em):')
  if (size) {
    editor.value.chain().focus().setMark('textStyle', { fontSize: size }).run()
  }
}

const insertTable = () => {
  editor.value.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
}

// Recipients handling
const recipientInput = ref(null)
const currentEmailInput = ref('')
const emailPills = ref([]) // Array of { address: string, status: 'valid' | 'invalid' | 'duplicate', reason: string }
const selectedGroups = ref([])
const expandedGroups = ref([])

// Attachments handling
const attachmentInput = ref(null)
const attachments = ref([]) // Array of File objects
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB in bytes

// Email validation regex
const validateEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email.trim())
}

// Get validation error message
const getValidationError = (email) => {
  const trimmed = email.trim()

  if (!trimmed) {
    return 'Email cannot be empty'
  }

  if (!trimmed.includes('@')) {
    return 'Email must contain @ symbol'
  }

  const parts = trimmed.split('@')
  if (parts.length !== 2) {
    return 'Email must have exactly one @ symbol'
  }

  if (!parts[0]) {
    return 'Email must have a username before @'
  }

  if (!parts[1]) {
    return 'Email must have a domain after @'
  }

  if (!parts[1].includes('.')) {
    return 'Domain must contain a dot (.)'
  }

  const domainParts = parts[1].split('.')
  if (domainParts.some(part => !part)) {
    return 'Domain parts cannot be empty'
  }

  if (/\s/.test(trimmed)) {
    return 'Email cannot contain spaces'
  }

  return 'Invalid email format'
}

// Get all emails including from groups
const getAllEmails = () => {
  const emails = new Set()

  // Add emails from groups
  selectedGroups.value.forEach(group => {
    if (group.emails && Array.isArray(group.emails)) {
      group.emails.forEach(email => emails.add(email.toLowerCase()))
    }
  })

  // Add emails from pills
  emailPills.value.forEach(pill => {
    emails.add(pill.address.toLowerCase())
  })

  return emails
}

// Check if email is duplicate and return source
const getDuplicateSource = (email) => {
  const normalizedEmail = email.toLowerCase().trim()

  // Check in existing pills
  const pillIndex = emailPills.value.findIndex(pill =>
    pill.address.toLowerCase() === normalizedEmail
  )

  if (pillIndex > -1) {
    return `Already added manually`
  }

  // Check in groups
  for (const group of selectedGroups.value) {
    if (group.emails && group.emails.some(groupEmail =>
      groupEmail.toLowerCase() === normalizedEmail
    )) {
      return `Already in group: ${group.name}`
    }
  }

  return null
}

// Add email pill
const addEmailPill = (email) => {
  const trimmedEmail = email.trim()
  if (!trimmedEmail) return

  let status = 'valid'
  let reason = ''

  // Validate email format
  if (!validateEmail(trimmedEmail)) {
    status = 'invalid'
    reason = getValidationError(trimmedEmail)
  } else {
    // Check for duplicates
    const duplicateSource = getDuplicateSource(trimmedEmail)
    if (duplicateSource) {
      status = 'duplicate'
      reason = duplicateSource
    }
  }

  emailPills.value.push({
    address: trimmedEmail,
    status: status,
    reason: reason
  })

  currentEmailInput.value = ''
}

// Remove email pill
const removeEmailPill = (index) => {
  emailPills.value.splice(index, 1)
}

// Handle email input keydown
const handleEmailInputKeydown = (event) => {
  if (event.key === ',' || event.key === 'Enter') {
    event.preventDefault()
    addEmailPill(currentEmailInput.value)
  } else if (event.key === 'Backspace' && currentEmailInput.value === '' && emailPills.value.length > 0) {
    // Remove last pill on backspace if input is empty
    emailPills.value.pop()
  }
}

// Handle email paste
const handleEmailPaste = (event) => {
  event.preventDefault()
  const pastedText = event.clipboardData?.getData('text') || ''

  // Split by common separators
  const emails = pastedText.split(/[,;\s\n]+/).filter(e => e.trim())

  emails.forEach(email => {
    addEmailPill(email)
  })
}

// Handle email input blur
const handleEmailInputBlur = () => {
  if (currentEmailInput.value.trim()) {
    addEmailPill(currentEmailInput.value)
  }
}

// Toggle group expansion
const toggleGroupExpansion = (groupName) => {
  const index = expandedGroups.value.indexOf(groupName)
  if (index > -1) {
    expandedGroups.value.splice(index, 1)
  } else {
    expandedGroups.value.push(groupName)
  }
}

// Remove group
const removeGroup = (groupName) => {
  const index = selectedGroups.value.findIndex(g => g.name === groupName)
  if (index > -1) {
    selectedGroups.value.splice(index, 1)
    // Remove from expanded groups if present
    const expandedIndex = expandedGroups.value.indexOf(groupName)
    if (expandedIndex > -1) {
      expandedGroups.value.splice(expandedIndex, 1)
    }
  }
  // Update form data
  formData.value.email_group = selectedGroups.value.map(group => ({
    email_group: group.name
  }))
}

// Attachment handling functions
const handleFileAttachment = (event) => {
  const files = Array.from(event.target.files || [])

  files.forEach(file => {
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      alert(`File "${file.name}" is too large. Maximum size is 10MB.`)
      return
    }

    // Check for duplicates
    const isDuplicate = attachments.value.some(
      existing => existing.name === file.name && existing.size === file.size
    )

    if (isDuplicate) {
      alert(`File "${file.name}" is already attached.`)
      return
    }

    // Add file to attachments
    attachments.value.push(file)
  })

  // Reset input
  if (attachmentInput.value) {
    attachmentInput.value.value = ''
  }
}

const removeAttachment = (index) => {
  attachments.value.splice(index, 1)
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const isImageFile = (file) => {
  return file.type.startsWith('image/')
}

const isPDFFile = (file) => {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

const totalAttachmentSize = computed(() => {
  return attachments.value.reduce((total, file) => total + file.size, 0)
})

// Group creation helper functions
const generateTempGroupName = () => {
  const randomSuffix = Math.random().toString(36).substring(2, 8)
  return `temp-grp-${randomSuffix}`
}

const createEmailGroup = async (groupName, emails, isTemporary = false) => {
  try {
    console.log(`Creating email group: ${groupName}`, emails)

    // Create Email Group document
    const emailGroupDoc = {
      doctype: 'Email Group',
      title: groupName,
    }

    const createdGroup = await call('frappe.client.insert', {
      doc: emailGroupDoc
    })

    console.log('Email Group created:', createdGroup)

    // Add emails to the group as separate Email Group Member documents
    for (const email of emails) {
      const emailGroupMember = {
        doctype: 'Email Group Member',
        email_group: createdGroup.name, // Link to the Email Group
        email: email,
        unsubscribed: 0
      }

      await call('frappe.client.insert', {
        doc: emailGroupMember
      })
    }

    console.log(`Added ${emails.length} members to group ${groupName}`)

    return {
      name: createdGroup.name,
      title: groupName,
      email_count: emails.length,
      emails: emails,
      isTemporary: isTemporary
    }
  } catch (error) {
    console.error('Error creating email group:', error)
    throw new Error(`Failed to create email group: ${error.message || error}`)
  }
}

const showGroupNamingPrompt = (emails, message, callback) => {
  pendingGroupEmails.value = emails
  groupNamingMessage.value = message
  groupNamingCallback.value = callback
  newGroupName.value = ''
  showGroupNamingDialog.value = true

  // Focus the input after dialog opens
  setTimeout(() => {
    if (groupNameInput.value) {
      groupNameInput.value.focus()
    }
  }, 100)
}

const cancelGroupNaming = () => {
  showGroupNamingDialog.value = false
  pendingGroupEmails.value = []
  groupNamingMessage.value = ''
  groupNamingCallback.value = null
  newGroupName.value = ''
}

const skipGroupNaming = async () => {
  showGroupNamingDialog.value = false

  if (groupNamingCallback.value) {
    // Create temporary group
    const tempGroupName = generateTempGroupName()
    const createdGroup = await createEmailGroup(tempGroupName, pendingGroupEmails.value, true)
    groupNamingCallback.value(createdGroup)
  }

  cancelGroupNaming()
}

const confirmGroupNaming = async () => {
  showGroupNamingDialog.value = false

  if (groupNamingCallback.value) {
    const groupName = newGroupName.value.trim() || generateTempGroupName()
    const isTemporary = !newGroupName.value.trim()
    const createdGroup = await createEmailGroup(groupName, pendingGroupEmails.value, isTemporary)
    groupNamingCallback.value(createdGroup)
  }

  cancelGroupNaming()
}

// Form data based on Newsletter doctype
const formData = ref({
  // From section
  sender_name: '',
  sender_email: '',
  send_from: '',

  // Recipients (will be handled separately)
  email_group: [],

  // Subject & Content
  subject: '',
  content_type: 'Rich Text',
  message: '',
  message_md: '',
  message_html: '',

  // Options
  send_unsubscribe_link: true,
  send_webview_link: false,
  published: false,
  route: '',

  // Scheduling
  schedule_sending: false,
  schedule_send: '',

  // Campaign
  campaign: '',

  // Attachments (to be implemented later if needed)
  attachments: []
})

// Computed properties
const validEmailCount = computed(() => {
  return emailPills.value.filter(pill => pill.status === 'valid').length
})

const invalidEmailCount = computed(() => {
  return emailPills.value.filter(pill => pill.status === 'invalid').length
})

const duplicateEmailCount = computed(() => {
  return emailPills.value.filter(pill => pill.status === 'duplicate').length
})

const totalRecipientCount = computed(() => {
  const groupEmailCount = selectedGroups.value.reduce((count, group) => count + (group.email_count || 0), 0)
  const validPillCount = validEmailCount.value
  return groupEmailCount + validPillCount
})

// Watch for content type changes to clear other message fields
watch(() => formData.value.content_type, (newType, oldType) => {
  if (newType !== 'Rich Text') formData.value.message = ''
  if (newType !== 'Markdown') formData.value.message_md = ''
  if (newType !== 'HTML') formData.value.message_html = ''
})

// Watch for message changes to sync with Tiptap editor
watch(() => formData.value.message, (newMessage) => {
  if (editor.value && editor.value.getHTML() !== newMessage) {
    editor.value.commands.setContent(newMessage || '', false)
  }
})

// Watch sendLater to update schedule_sending
watch(sendLater, (value) => {
  formData.value.schedule_sending = value
  if (!value) {
    formData.value.schedule_send = ''
  }
})

// Watch published to generate route
watch(() => formData.value.published, (isPublished) => {
  if (isPublished && formData.value.subject && !formData.value.route) {
    formData.value.route = `newsletter/${formData.value.subject.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')}`
  } else if (!isPublished) {
    formData.value.route = ''
  }
})

// Methods
const closeDialog = () => {
  emit('close')
  isDialogOpen.value = false
}

const resetForm = () => {
  // Auto-populate sender info with current user
  const currentUser = session.user || 'Administrator'

  console.log('Resetting form for user:', currentUser)
  console.log('Session object:', session)

  // Default values - ensure these are NEVER empty
  // Try to use session.user as email if it looks like an email
  let userEmail = currentUser.includes('@') ? currentUser : `${currentUser}@yourcompany.com`
  let senderName = currentUser === 'Administrator' ? 'System Administrator' : currentUser

  console.log('Default sender email:', userEmail)
  console.log('Default sender name:', senderName)

  // Initialize form with defaults first
  formData.value = {
    sender_name: senderName,
    sender_email: userEmail,  // This MUST have a value
    send_from: senderName,
    email_group: [],
    subject: '',
    content_type: 'Rich Text',
    message: '',
    message_md: '',
    message_html: '',
    send_unsubscribe_link: true,
    send_webview_link: false,
    published: false,
    route: '',
    schedule_sending: false,
    schedule_send: '',
    campaign: '',
    attachments: []
  }

  console.log('Form initialized with sender_email:', formData.value.sender_email)

  // Fetch user's actual email from Frappe asynchronously (non-blocking)
  call('frappe.client.get', {
    doctype: 'User',
    name: currentUser
  }).then(userDoc => {
    console.log('Fetched user document:', userDoc)
    if (userDoc && userDoc.email) {
      const realEmail = userDoc.email
      const realName = userDoc.full_name || userDoc.first_name || currentUser

      console.log('Updating sender email to:', realEmail)
      console.log('Updating sender name to:', realName)

      // Only update if we got a real email
      if (realEmail && realEmail.includes('@')) {
        formData.value.sender_email = realEmail
        formData.value.sender_name = realName
        formData.value.send_from = realName

        console.log('Updated form sender_email:', formData.value.sender_email)
      } else {
        console.warn('User document email is invalid, keeping default:', realEmail)
      }
    } else {
      console.warn('User document missing email field, keeping default')
    }
  }).catch(error => {
    console.error('Error fetching user email:', error)
    console.log('Keeping default sender email:', formData.value.sender_email)
    // Keep the default values already set - they should NEVER be empty
  })

  // Clear recipients
  emailPills.value = []
  currentEmailInput.value = ''
  selectedGroups.value = []
  expandedGroups.value = []
  sendLater.value = false

  // Clear attachments
  attachments.value = []

  // Clear Tiptap editor
  if (editor.value) {
    editor.value.commands.setContent('', false)
  }
}

const handleGroupsSelected = (groups) => {
  selectedGroups.value = groups
  formData.value.email_group = groups.map(group => ({
    email_group: group.name
  }))
}

const saveDraft = async () => {
  const proceedWithSave = async (finalGroups) => {
    try {
      isSaving.value = true

      // Upload attachments first if any
      const uploadedAttachments = []
      if (attachments.value.length > 0) {
        console.log(`Uploading ${attachments.value.length} attachments...`)
        for (const file of attachments.value) {
          try {
            const formData = new FormData()
            formData.append('file', file, file.name)
            formData.append('is_private', '0')
            // Don't attach to a document yet - we'll link it via the Newsletter attachments child table

            // Use native fetch for file upload as frappe-ui call doesn't handle FormData properly
            // Get CSRF token from cookies
            const getCookie = (name) => {
              const value = `; ${document.cookie}`
              const parts = value.split(`; ${name}=`)
              if (parts.length === 2) return parts.pop().split(';').shift()
              return null
            }

            const csrfToken = getCookie('csrf_token')

            const uploadResponse = await fetch('/api/method/upload_file', {
              method: 'POST',
              headers: {
                'X-Frappe-CSRF-Token': csrfToken,
              },
              body: formData
            })

            if (!uploadResponse.ok) {
              const errorText = await uploadResponse.text()
              console.error('Upload error response:', errorText)
              throw new Error(`Upload failed with status ${uploadResponse.status}`)
            }

            const result = await uploadResponse.json()
            if (result.message) {
              console.log('File uploaded:', result.message)
              uploadedAttachments.push({
                attachment: result.message.file_url
              })
            } else {
              throw new Error('Upload response missing file_url')
            }
          } catch (uploadError) {
            console.error('Error uploading file:', file.name, uploadError)
            throw new Error(`Failed to upload file "${file.name}": ${uploadError.message || uploadError}`)
          }
        }
        console.log('All attachments uploaded successfully:', uploadedAttachments)
      }

      // Prepare Newsletter document data
      const newsletterData = {
        doctype: 'Newsletter',
        subject: formData.value.subject,
        sender_name: formData.value.sender_name || session.user,
        sender_email: formData.value.sender_email,
        send_from: formData.value.send_from || `${formData.value.sender_name} <${formData.value.sender_email}>`,
        content_type: formData.value.content_type,
        message: formData.value.message || '',
        message_md: formData.value.message_md || '',
        message_html: formData.value.message_html || '',
        send_unsubscribe_link: formData.value.send_unsubscribe_link ? 1 : 0,
        send_webview_link: formData.value.send_webview_link ? 1 : 0,
        published: formData.value.published ? 1 : 0,
        route: formData.value.route || '',
        schedule_sending: formData.value.schedule_sending ? 1 : 0,
        schedule_send: formData.value.schedule_send || null,
        campaign: formData.value.campaign || '',
        email_group: finalGroups.map(group => ({
          email_group: group.name
        })),
        attachments: uploadedAttachments,
      }

      console.log('Saving Newsletter draft:', newsletterData)

      // Save Newsletter document using Frappe API
      const result = await call('frappe.client.insert', {
        doc: newsletterData
      })

      console.log('Newsletter saved:', result)

      // Emit success event
      emit('email-sent', {
        type: 'success',
        subject: result.subject,
        name: result.name,
        recipientCount: totalRecipientCount.value,
        action: 'draft_saved',
        message: `Newsletter draft "${result.subject}" saved successfully!`
      })

      // Close dialog
      closeDialog()

    } catch (error) {
      console.error('Error saving newsletter:', error)

      // Emit error event
      emit('email-sent', {
        type: 'error',
        subject: formData.value.subject,
        name: null,
        recipientCount: 0,
        action: 'draft_save_failed',
        message: `Failed to save newsletter: ${error.message || error}`
      })
    } finally {
      isSaving.value = false
    }
  }

  try {
    // Validate required fields for Newsletter doctype
    if (!formData.value.subject) {
      throw new Error('Subject is required')
    }

    if (!formData.value.sender_email) {
      throw new Error('Sender Email is required')
    }

    // Validate at least one recipient group is selected
    if (selectedGroups.value.length === 0 && validEmailCount.value === 0) {
      throw new Error('At least one email group or recipient is required')
    }

    const validEmails = emailPills.value
      .filter(pill => pill.status === 'valid')
      .map(pill => pill.address)

    const hasSelectedGroups = selectedGroups.value.length > 0
    const hasManualEmails = validEmails.length > 0

    // Scenario 1: Only email groups selected - no prompt needed
    if (hasSelectedGroups && !hasManualEmails) {
      await proceedWithSave(selectedGroups.value)
      return
    }

    // Scenario 2: Only 1 manual email - create temp group automatically
    if (!hasSelectedGroups && validEmails.length === 1) {
      const tempGroupName = generateTempGroupName()
      const createdGroup = await createEmailGroup(tempGroupName, validEmails, true)
      await proceedWithSave([createdGroup])
      return
    }

    // Scenario 3: Multiple manual emails OR mix of groups + manual emails - ask for group name
    let emailsToGroup = [...validEmails]
    let message = ''

    if (hasSelectedGroups && hasManualEmails) {
      // Mix: Include emails from selected groups + manual emails
      selectedGroups.value.forEach(group => {
        if (group.emails) {
          emailsToGroup.push(...group.emails)
        }
      })
      // Remove duplicates
      emailsToGroup = [...new Set(emailsToGroup)]
      message = 'You have selected email groups and added individual emails. Would you like to save all recipients as a new group for future use?'
    } else {
      // Only multiple manual emails
      message = 'Would you like to save these recipients as a group for future use?'
    }

    showGroupNamingPrompt(emailsToGroup, message, async (createdGroup) => {
      // If mixing with existing groups, use only the newly created group
      // Otherwise use the created group
      const finalGroups = hasSelectedGroups ? [createdGroup] : [createdGroup]
      await proceedWithSave(finalGroups)
    })

  } catch (error) {
    console.error('Error in save draft:', error)
    alert(`Error: ${error.message || error}`)
    isSaving.value = false
  }
}

const sendEmail = async () => {
  const proceedWithSend = async (finalGroups) => {
    try {
      isSubmitting.value = true

      // Upload attachments first if any
      const uploadedAttachments = []
      if (attachments.value.length > 0) {
        console.log(`Uploading ${attachments.value.length} attachments...`)
        for (const file of attachments.value) {
          try {
            const formData = new FormData()
            formData.append('file', file, file.name)
            formData.append('is_private', '0')
            // Don't attach to a document yet - we'll link it via the Newsletter attachments child table

            // Use native fetch for file upload as frappe-ui call doesn't handle FormData properly
            // Get CSRF token from cookies
            const getCookie = (name) => {
              const value = `; ${document.cookie}`
              const parts = value.split(`; ${name}=`)
              if (parts.length === 2) return parts.pop().split(';').shift()
              return null
            }

            const csrfToken = getCookie('csrf_token')

            const uploadResponse = await fetch('/api/method/upload_file', {
              method: 'POST',
              headers: {
                'X-Frappe-CSRF-Token': csrfToken,
              },
              body: formData
            })

            if (!uploadResponse.ok) {
              const errorText = await uploadResponse.text()
              console.error('Upload error response:', errorText)
              throw new Error(`Upload failed with status ${uploadResponse.status}`)
            }

            const result = await uploadResponse.json()
            if (result.message) {
              console.log('File uploaded:', result.message)
              uploadedAttachments.push({
                attachment: result.message.file_url
              })
            } else {
              throw new Error('Upload response missing file_url')
            }
          } catch (uploadError) {
            console.error('Error uploading file:', file.name, uploadError)
            throw new Error(`Failed to upload file "${file.name}": ${uploadError.message || uploadError}`)
          }
        }
        console.log('All attachments uploaded successfully:', uploadedAttachments)
      }

      // Prepare Newsletter document data
      const newsletterData = {
        doctype: 'Newsletter',
        subject: formData.value.subject,
        sender_name: formData.value.sender_name || session.user,
        sender_email: formData.value.sender_email,
        send_from: formData.value.send_from || `${formData.value.sender_name} <${formData.value.sender_email}>`,
        content_type: formData.value.content_type,
        message: formData.value.message || '',
        message_md: formData.value.message_md || '',
        message_html: formData.value.message_html || '',
        send_unsubscribe_link: formData.value.send_unsubscribe_link ? 1 : 0,
        send_webview_link: formData.value.send_webview_link ? 1 : 0,
        published: formData.value.published ? 1 : 0,
        route: formData.value.route || '',
        schedule_sending: formData.value.schedule_sending ? 1 : 0,
        schedule_send: formData.value.schedule_send || null,
        campaign: formData.value.campaign || '',
        email_group: finalGroups.map(group => ({
          email_group: group.name
        })),
        attachments: uploadedAttachments,
      }

      console.log('Creating Newsletter:', newsletterData)

      // Step 1: Save Newsletter document using Frappe API
      // Note: Frappe will auto-generate a unique name based on the subject if there's a duplicate
      let savedNewsletter
      try {
        savedNewsletter = await call('frappe.client.insert', {
          doc: newsletterData
        })
      } catch (error) {
        // If duplicate entry error, try with a timestamp suffix
        if (error.message && error.message.includes('DuplicateEntryError')) {
          const timestamp = Date.now()
          newsletterData.subject = `${formData.value.subject} (${timestamp})`
          savedNewsletter = await call('frappe.client.insert', {
            doc: newsletterData
          })
        } else {
          throw error
        }
      }

      console.log('Newsletter saved:', savedNewsletter)
      console.log('Email groups in newsletter:', finalGroups.map(g => g.name))

      // Log email group members to verify they exist
      for (const group of finalGroups) {
        console.log(`Checking members for group: ${group.name}`)
        try {
          const members = await call('frappe.client.get_list', {
            doctype: 'Email Group Member',
            fields: ['email', 'email_group', 'unsubscribed'],
            filters: [['email_group', '=', group.name]],
            limit_page_length: 1000
          })
          console.log(`Group ${group.name} has ${members.length} members:`, members)
        } catch (err) {
          console.error(`Error checking members for ${group.name}:`, err)
        }
      }

      // Step 2: Send the newsletter immediately (or schedule if configured)
      if (formData.value.schedule_sending && formData.value.schedule_send) {
        // Newsletter will be sent at scheduled time
        emit('email-sent', {
          type: 'info',
          subject: savedNewsletter.subject,
          name: savedNewsletter.name,
          recipientCount: totalRecipientCount.value,
          scheduled: true,
          action: 'scheduled',
          message: `Newsletter "${savedNewsletter.subject}" scheduled to send at ${formData.value.schedule_send}`
        })
      } else {
        // Send immediately using the Newsletter.send_emails() whitelisted method
        console.log('Sending newsletter:', savedNewsletter.name)

        // Call send_emails on the saved newsletter using Frappe's run_doc_method API
        // This requires the full document object
        await call('run_doc_method', {
          docs: savedNewsletter,
          method: 'send_emails'
        })

        // Emit success event
        emit('email-sent', {
          type: 'success',
          subject: savedNewsletter.subject,
          name: savedNewsletter.name,
          recipientCount: totalRecipientCount.value,
          scheduled: false,
          action: 'sent',
          message: `Newsletter "${savedNewsletter.subject}" has been queued for sending to ${totalRecipientCount.value} recipients!`
        })
      }

      // Close dialog and reset form
      closeDialog()

    } catch (error) {
      console.error('Error sending newsletter:', error)

      // Emit error event
      emit('email-sent', {
        type: 'error',
        subject: formData.value.subject,
        name: null,
        recipientCount: 0,
        scheduled: false,
        action: 'send_failed',
        message: `Failed to send newsletter: ${error.message || error}`
      })
    } finally {
      isSubmitting.value = false
    }
  }

  try {
    // Validate required fields for Newsletter doctype
    if (!formData.value.subject) {
      throw new Error('Subject is required')
    }

    if (!formData.value.sender_email) {
      console.error('Sender email is missing! Current formData:', formData.value)
      throw new Error('Sender Email is required')
    }

    console.log('Sending email with sender:', formData.value.sender_email)

    // Validate message content based on type
    const messageField = {
      'Rich Text': 'message',
      'Markdown': 'message_md',
      'HTML': 'message_html'
    }[formData.value.content_type]

    if (!formData.value[messageField]) {
      throw new Error('Message content is required')
    }

    // Validate at least one recipient group is selected
    if (selectedGroups.value.length === 0 && validEmailCount.value === 0) {
      throw new Error('At least one email group or recipient is required')
    }

    const validEmails = emailPills.value
      .filter(pill => pill.status === 'valid')
      .map(pill => pill.address)

    const hasSelectedGroups = selectedGroups.value.length > 0
    const hasManualEmails = validEmails.length > 0

    // Scenario 1: Only email groups selected - no prompt needed
    if (hasSelectedGroups && !hasManualEmails) {
      await proceedWithSend(selectedGroups.value)
      return
    }

    // Scenario 2: Only 1 manual email - create temp group automatically
    if (!hasSelectedGroups && validEmails.length === 1) {
      const tempGroupName = generateTempGroupName()
      const createdGroup = await createEmailGroup(tempGroupName, validEmails, true)
      await proceedWithSend([createdGroup])
      return
    }

    // Scenario 3: Multiple manual emails OR mix of groups + manual emails - ask for group name
    let emailsToGroup = [...validEmails]
    let message = ''

    if (hasSelectedGroups && hasManualEmails) {
      // Mix: Include emails from selected groups + manual emails
      selectedGroups.value.forEach(group => {
        if (group.emails) {
          emailsToGroup.push(...group.emails)
        }
      })
      // Remove duplicates
      emailsToGroup = [...new Set(emailsToGroup)]
      message = 'You have selected email groups and added individual emails. Would you like to save all recipients as a new group for future use?'
    } else {
      // Only multiple manual emails
      message = 'Would you like to save these recipients as a group for future use?'
    }

    showGroupNamingPrompt(emailsToGroup, message, async (createdGroup) => {
      // If mixing with existing groups, use only the newly created group
      const finalGroups = hasSelectedGroups ? [createdGroup] : [createdGroup]
      await proceedWithSend(finalGroups)
    })

  } catch (error) {
    console.error('Error in send email:', error)
    alert(`Error: ${error.message || error}`)
    isSubmitting.value = false
  }
}

// Reset form when dialog is opened
watch(() => props.show, (isOpen) => {
  if (isOpen) {
    resetForm()
  }
})

// Cleanup editor on component unmount
onBeforeUnmount(() => {
  if (editor.value) {
    editor.value.destroy()
  }
})
</script>

<style>
/* Tiptap Editor Styles */
.tiptap-editor {
  @apply w-full;
}

.tiptap-editor .ProseMirror {
  @apply px-3 py-2 focus:outline-none min-h-[200px] max-h-[400px] overflow-y-auto;
}

.tiptap-editor .ProseMirror:focus {
  @apply outline-none;
}

/* Placeholder */
.tiptap-editor .ProseMirror p.is-editor-empty:first-child::before {
  content: 'Compose your email message...';
  @apply text-gray-400;
  float: left;
  height: 0;
  pointer-events: none;
}

/* Typography */
.tiptap-editor .ProseMirror h1 {
  @apply text-2xl font-bold mt-4 mb-2;
}

.tiptap-editor .ProseMirror h2 {
  @apply text-xl font-bold mt-3 mb-2;
}

.tiptap-editor .ProseMirror h3 {
  @apply text-lg font-bold mt-2 mb-1;
}

.tiptap-editor .ProseMirror p {
  @apply my-2;
}

.tiptap-editor .ProseMirror ul {
  @apply list-disc ml-6 my-2;
}

.tiptap-editor .ProseMirror ol {
  @apply list-decimal ml-6 my-2;
}

.tiptap-editor .ProseMirror li {
  @apply my-1;
}

.tiptap-editor .ProseMirror blockquote {
  @apply border-l-4 border-gray-300 pl-4 italic my-2;
}

.tiptap-editor .ProseMirror hr {
  @apply my-4 border-t border-gray-300;
}

.tiptap-editor .ProseMirror strong {
  @apply font-bold;
}

.tiptap-editor .ProseMirror em {
  @apply italic;
}

.tiptap-editor .ProseMirror u {
  @apply underline;
}

.tiptap-editor .ProseMirror s {
  @apply line-through;
}

.tiptap-editor .ProseMirror code {
  @apply bg-gray-100 px-1 py-0.5 rounded text-sm font-mono;
}

.tiptap-editor .ProseMirror pre {
  @apply bg-gray-100 p-3 rounded my-2 overflow-x-auto;
}

.tiptap-editor .ProseMirror pre code {
  @apply bg-transparent p-0;
}

/* Images with Resize */
.tiptap-editor .ProseMirror img {
  @apply max-w-full h-auto rounded my-2;
  cursor: pointer;
  display: inline-block;
}

.tiptap-editor .ProseMirror img.ProseMirror-selectednode {
  @apply outline outline-2 outline-blue-500;
}

/* Image Resize Wrapper */
.tiptap-editor .ProseMirror .image-resizer {
  display: inline-block;
  position: relative;
  line-height: 0;
}

.tiptap-editor .ProseMirror .image-resizer img {
  display: block;
  margin: 0;
}

/* Resize Handles */
.tiptap-editor .ProseMirror .image-resizer .resize-trigger {
  position: absolute;
  width: 10px;
  height: 10px;
  background: #3b82f6;
  border: 2px solid white;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  cursor: nwse-resize;
  z-index: 10;
}

.tiptap-editor .ProseMirror .image-resizer .resize-trigger.right {
  right: -5px;
  bottom: -5px;
}

.tiptap-editor .ProseMirror .image-resizer .resize-trigger.left {
  left: -5px;
  bottom: -5px;
  cursor: nesw-resize;
}

.tiptap-editor .ProseMirror .image-resizer .resize-trigger.top-right {
  right: -5px;
  top: -5px;
  cursor: nesw-resize;
}

.tiptap-editor .ProseMirror .image-resizer .resize-trigger.top-left {
  left: -5px;
  top: -5px;
  cursor: nwse-resize;
}

/* Resize cursor during drag */
.tiptap-editor .ProseMirror .image-resizer.resizing {
  cursor: nwse-resize;
}

.tiptap-editor .ProseMirror .image-resizer.resizing img {
  pointer-events: none;
}

/* Tables */
.tiptap-editor .ProseMirror table {
  @apply border-collapse table-auto w-full my-4;
}

.tiptap-editor .ProseMirror table td,
.tiptap-editor .ProseMirror table th {
  @apply border border-gray-300 px-3 py-2 text-left min-w-[100px];
  position: relative;
}

.tiptap-editor .ProseMirror table th {
  @apply bg-gray-100 font-bold;
}

.tiptap-editor .ProseMirror table .selectedCell {
  @apply bg-blue-50;
}

.tiptap-editor .ProseMirror table .column-resize-handle {
  position: absolute;
  right: -2px;
  top: 0;
  bottom: 0;
  width: 4px;
  background-color: #3b82f6;
  pointer-events: none;
}

/* Text Alignment */
.tiptap-editor .ProseMirror [style*="text-align: left"] {
  text-align: left;
}

.tiptap-editor .ProseMirror [style*="text-align: center"] {
  text-align: center;
}

.tiptap-editor .ProseMirror [style*="text-align: right"] {
  text-align: right;
}

.tiptap-editor .ProseMirror [style*="text-align: justify"] {
  text-align: justify;
}

/* Highlights */
.tiptap-editor .ProseMirror mark {
  @apply px-1 rounded;
}
</style>