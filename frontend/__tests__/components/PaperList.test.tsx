import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PaperList from '@/app/components/PaperList'

const mockApi = vi.hoisted(() => ({
  listPapers: vi.fn(),
  search: vi.fn(),
  deletePaper: vi.fn(),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual('@/lib/api')
  return {
    ...actual,
    api: mockApi,
  }
})

const samplePapers = [
  {
    paper_id: 'paper-1',
    title: 'Paper One',
    abstract: 'First abstract',
    relevance_score: 0.91,
  },
  {
    paper_id: 'paper-2',
    title: 'Paper Two',
    abstract: 'Second abstract',
    relevance_score: 0.77,
  },
]

describe('PaperList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApi.listPapers.mockResolvedValue({ papers: samplePapers })
    mockApi.search.mockResolvedValue({ papers: samplePapers })
    mockApi.deletePaper.mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('renders selected styles when selectedPaperId matches a paper', async () => {
    render(<PaperList selectedPaperId="paper-1" />)

    const selectedCard = await screen.findByRole('option', { name: /paper one/i })
    const nonSelectedCard = screen.getByRole('option', { name: /paper two/i })

    expect(selectedCard).toHaveAttribute('aria-selected', 'true')
    expect(selectedCard.className).toContain('border-primary-400')
    expect(selectedCard.className).toContain('dark:bg-primary-900/50')
    expect(selectedCard.querySelector('span[aria-hidden="true"]')).toBeInTheDocument()

    expect(nonSelectedCard).toHaveAttribute('aria-selected', 'false')
    expect(nonSelectedCard.className).toContain('border-gray-200')
    expect(nonSelectedCard.querySelector('span[aria-hidden="true"]')).not.toBeInTheDocument()
  })

  it('deselects when clicking outside paper cards in the papers tab', async () => {
    const onPaperDeselect = vi.fn()
    const user = userEvent.setup()
    render(<PaperList selectedPaperId="paper-1" onPaperDeselect={onPaperDeselect} />)

    const listbox = await screen.findByRole('listbox', { name: /paper list/i })
    await user.click(listbox)

    expect(onPaperDeselect).toHaveBeenCalledTimes(1)
  })

  it('calls onPaperSelect with the correct paper id when cards are clicked', async () => {
    const onPaperSelect = vi.fn()
    const user = userEvent.setup()
    render(<PaperList selectedPaperId="paper-1" onPaperSelect={onPaperSelect} />)

    const selectedCard = await screen.findByRole('option', { name: /paper one/i })
    const nonSelectedCard = screen.getByRole('option', { name: /paper two/i })

    await user.click(selectedCard)
    await user.click(nonSelectedCard)

    expect(onPaperSelect).toHaveBeenCalledWith('paper-1')
    expect(onPaperSelect).toHaveBeenCalledWith('paper-2')
    expect(onPaperSelect).toHaveBeenCalledTimes(2)
  })

  it('does not call onPaperSelect when delete is clicked', async () => {
    const onPaperSelect = vi.fn()
    const user = userEvent.setup()
    render(<PaperList onPaperSelect={onPaperSelect} />)

    await screen.findByRole('option', { name: /paper one/i })
    const deleteButtons = screen.getAllByTitle('Delete paper')

    await user.click(deleteButtons[0])

    expect(window.confirm).toHaveBeenCalled()
    expect(mockApi.deletePaper).toHaveBeenCalledWith('paper-1')
    expect(onPaperSelect).not.toHaveBeenCalled()
    await waitFor(() => {
      expect(mockApi.listPapers).toHaveBeenCalledTimes(2)
    })
  })
})
